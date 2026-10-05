import json, os, re, sys
from pathlib import Path
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from openai import OpenAI
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware

DATA = Path(__file__).resolve().parents[1] / "data"
sys.path.append(str(DATA.parent / "pipeline"))
from cleaning import norm   # نفس تطبيع النص العربي المستخدم في الـpipeline
load_dotenv(DATA.parent / ".env")
MODEL = os.environ.get("GROQ_MODEL", "openai/gpt-oss-120b")
client = OpenAI(api_key=os.environ.get("GROQ_API_KEY") or "missing", base_url="https://api.groq.com/openai/v1")
app = FastAPI(title="Raheeq API")
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:5173"], allow_methods=["GET", "POST"], allow_headers=["*"])

def load(p: Path):
    return json.loads(p.read_text("utf-8"))

@app.get("/api/chapters")
def chapters():
    return load(DATA / "index.json")

@app.get("/api/chapters/{cid}")
def chapter(cid: str):
    base = DATA / "chapters" / f"{cid}.json"
    if not base.exists():
        raise HTTPException(404, "chapter not found")
    ch = load(base)
    extra = DATA / "llm" / f"{cid}.json"
    llm = load(extra) if extra.exists() else {}      # لو الـLLM لسه ما اشتغلش، الشابتر يظهر بالداتا بس
    for sec in ch["sections"]:                        # صياغة الـLLM لكل حدث (لو موجودة)
        for e in sec["events"]:
            rw = DATA / "rewrites" / f"{e['id']}.json"
            r = load(rw) if rw.exists() else {}
            e["story"], e["lesson"] = r.get("story"), r.get("lesson")
    ch["intro"], ch["conclusion"] = llm.get("intro"), llm.get("conclusion")
    ch["lessons"] = llm.get("lessons", [])
    ch["quiz"] = ch.pop("quiz_data") + llm.get("quiz", [])
    return ch


# ---------------- AI Understanding Check ----------------
MAX_DETAILS_CHARS = 5500     # أطول من كده الحدث مش بيتبعت للـLLM (حد Groq TPM) والفرونت بيخفي الـcheck
MAX_ANSWER_CHARS = 600
_EV = {}

def event(eid):
    if not _EV:
        for p in (DATA / "chapters").glob("ch*.json"):
            for sec in load(p)["sections"]:
                for e in sec["events"]:
                    _EV[e["id"]] = e
    return _EV.get(eid)

SYSTEM = """أنت مُقيِّم فهم لمتعلّم يقرأ حدثًا من السيرة النبوية. لا تشرح السيرة ولا تحكيها، ولا تكتب أي محتوى سيرة جديد.
يصلك JSON فيه event_title و event_details و user_answer (ما فهمه المتعلم بكلماته). مهمتك تحليل فهمه فقط، وأعد JSON فقط.
القواعد:
1. event_details هو المصدر الوحيد للتقييم. لا تضف معلومة منه خارجه، ولا تستخدم معرفتك العامة للتصحيح أو الاستكمال.
2. ما لم يرد في event_details لا تعتبره نقطة مطلوبة من المتعلم.
3. لا تعاقب المتعلم لأنه لم يذكر كل التفاصيل؛ ركّز على الفكرة أو الأفكار الأساسية. ليس امتحان حفظ.
4. لا تشترط ألفاظ النص؛ إعادة الصياغة الصحيحة دليل فهم، والمعنى الصحيح يُقبل بأي تعبير.
5. إن تضمن النص روايات أو معلومات غير مؤكدة فلا تصلحها من خارجه؛ قيّم فهمه لما ورد فيه فقط.
6. قد يحتوي الحدث على أكثر من نقطة زمنية؛ لا تفترضها نقطة واحدة متصلة.
7. لا تخترع نقطة أو سؤالًا لتصعّب التقييم.
8. good: فهم الفكرة الأساسية صحيحة. partial: فهم جزءًا مهمًا وترك نقطة أساسية أو أكثر. needs_review: إجابة لا تعكس فهمًا كافيًا، أو فيها فهم خاطئ مهم، أو فارغة/غير مفهومة/قصيرة جدًا بحيث لا تُقيَّم بموثوقية.
9. understood / missing / misunderstood: عبارات قصيرة جدًا بصياغة تعتمد على كلمات event_details نفسها (ليست شرحًا جديدًا).
10. feedback: جملة أو جملتان قصيرتان مشجعتان.
11. next_action: continue مع good، clarify مع partial، review مع needs_review."""

LEVELS = ("good", "partial", "needs_review")
LIST = {"type": "array", "items": {"type": "string"}}
SCHEMA = {"type": "object", "additionalProperties": False,
          "required": ["understanding_level", "understood", "missing", "misunderstood", "feedback", "next_action"],
          "properties": {"understanding_level": {"type": "string", "enum": list(LEVELS)}, "understood": LIST, "missing": LIST,
                         "misunderstood": LIST, "feedback": {"type": "string"},
                         "next_action": {"type": "string", "enum": ["continue", "clarify", "review"]}}}

def _w(t):
    return {re.sub(r"^ال", "", w) for w in norm(t).split() if len(w) > 3}

def snippets(details, items):
    """الجمل الأقرب لكل نقطة ناقصة من نص الحدث الأصلي نفسه (بدون LLM)."""
    sents = [x.strip() for x in re.split(r"(?<=[.!؟?])\s+", details) if len(x.strip()) > 20]
    out = []
    for it in items:
        iw = _w(it)
        best = max(sents, key=lambda x: len(iw & _w(x)), default=None)
        if iw and best and len(iw & _w(best)) >= 2 and best not in out:
            out.append(best)
    return out[:3]

class CheckIn(BaseModel):
    event_id: int
    user_answer: str

@app.post("/api/check")
def check(body: CheckIn):
    e = event(body.event_id)
    if not e:
        raise HTTPException(404, "event not found")
    if len(e["details"]) > MAX_DETAILS_CHARS:
        raise HTTPException(413, "event too long for check")
    ans = " ".join(body.user_answer.split())[:MAX_ANSWER_CHARS]
    if not ans:   # فاضية: needs_review بدون استدعاء LLM
        return {"understanding_level": "needs_review", "understood": [], "missing": [], "misunderstood": [],
                "feedback": "اكتب ما فهمته بكلماتك أولًا.", "next_action": "review", "review_snippets": []}
    payload = json.dumps({"event_title": e["title"], "event_details": e["details"], "user_answer": ans}, ensure_ascii=False)
    try:
        r = client.chat.completions.create(
            model=MODEL, temperature=0.2, max_completion_tokens=1200,
            messages=[{"role": "system", "content": SYSTEM}, {"role": "user", "content": payload}],
            extra_body={"reasoning_effort": "low"},
            response_format={"type": "json_schema", "json_schema": {"name": "understanding_check", "schema": SCHEMA}})
        res = json.loads(r.choices[0].message.content)
        assert res["understanding_level"] in LEVELS
        res = {k: res[k] for k in SCHEMA["required"]}
    except Exception as ex:
        print("check failed:", e["id"], str(ex)[:200])
        raise HTTPException(502, "llm failed")
    res["next_action"] = {"good": "continue", "partial": "clarify", "needs_review": "review"}[res["understanding_level"]]
    res["review_snippets"] = [] if res["understanding_level"] == "good" else snippets(e["details"], res["missing"] + res["misunderstood"])
    return res
