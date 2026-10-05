"""مقدمة + خاتمة (من ملخص الشابتر) ثم دروس عملية + Quiz (من نصوص أحداث مختارة كاملة تقريبًا) بالـLLM (Groq).
كل درس وسؤال لازم يجي معاه evidence منقول حرفيًا من نص الحدث، والكود بيرفضه لو مش موجود فعلًا في النص.
تشغيل:  python 02_generate_llm.py                  (كل الشابترز، بيكمل من حيث وقف)
        python 02_generate_llm.py --chapter ch01
        python 02_generate_llm.py --chapter ch01 --redo   (إعادة توليد الدروس والأسئلة فقط)
        python 02_generate_llm.py --model meta-llama/llama-4-scout-17b-16e-instruct   (موديل تاني؛ اللي اتعمل قبل كده بيتعدّى)
        python 02_generate_llm.py --min-quiz 3   (يعيد الدروس/الأسئلة للشابترز اللي أسئلتها أقل من 3)"""
import argparse, json, os, re, time
from collections import Counter
from difflib import SequenceMatcher
from collections import deque
from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI
from cleaning import llm_view, norm, leaks

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")
OUT = ROOT / "data" / "llm"; OUT.mkdir(exist_ok=True)
MODEL = os.environ.get("GROQ_MODEL", "openai/gpt-oss-120b")   # أو --model
SCHEMA_MODELS = ("openai/gpt-oss", "moonshotai/kimi-k2", "meta-llama/llama-4")   # بتدعم json_schema؛ غيرها بنستخدم JSON mode
PAYLOAD_BUDGET = 3500        # توكن تقريبي لملخص المقدمة/الخاتمة
CHARS_PER_TOKEN = 2.0
N_SAMPLE, SAMPLE_CHARS = 7, 600   # أحداث الدروس/الكويز: عددها وأقصى طول لنص كل حدث
TPM_BUDGET = 7000
client = OpenAI(api_key=os.environ["GROQ_API_KEY"], base_url="https://api.groq.com/openai/v1")

SYS_INTRO = """أنت محرر محتوى تعليمي عن السيرة النبوية من كتاب «الرحيق المختوم». يصلك ملخص مضغوط لأحداث شابتر.
اكتب intro (مقدمة تمهيدية 3-4 جمل) و conclusion (خاتمة 2-3 جمل) بعربية فصيحة سهلة ودافئة ومحترمة.
التزم حصريًا بالمعطيات: لا تخترع معلومات أو تواريخ أو أسماء أو حوارات أو مشاعر، ولا تستنبط أحكامًا، ولا تضف من معرفتك العامة، ولا تحوّل تاريخًا تقريبيًا إلى قاطع.
اكتب بالصلاة على النبي ﷺ عند ذكره."""

SYS_LQ = """أنت تصنع محتوى تعليميًا من أحداث السيرة النبوية (كتاب «الرحيق المختوم»). يصلك عدة أحداث، لكل حدث id وعنوان ونصه.

أولًا — lessons (من 0 إلى 3): دروس عملية تنفع الإنسان العادي في حياته اليومية، مثل: الصبر على الصعوبات، الأمانة في العمل، التخطيط، حسن التعامل مع الناس، الثبات تحت الضغط، العمل بروح الفريق، الوفاء بالعهد، اتخاذ القرار، الرحمة بالضعفاء.
- لكل درس: title (3-6 كلمات)، text (جملة أو جملتان تبيّنان ماذا يفعل القارئ في حياته)، event_id، evidence (نقل حرفي من نص الحدث يدل على الموقف الذي بُني عليه الدرس).
- الدرس يستند إلى سلوك أو موقف مذكور صراحة في نص الحدث، دون استنتاج معنى غير مذكور.
- ممنوع: المعاني التعبدية والروحانية والغيبية (الخشوع، القرب من الله، اللقاء الإلهي...)، وأحكام الفقه، وتفسير الوحي والغيبيات، وأي ادعاء عن نوايا أو مشاعر لم تُذكر.
- لا تُجبر نفسك: إن لم يوجد درس عملي واضح فأعد lessons مصفوفة فارغة. ولا تكرر المعنى نفسه.

ثانيًا — quiz: أسئلة اختيار من متعدد، كل سؤال من حدث مختلف.
- سؤال واضح عن معلومة صريحة في نص الحدث (من/أين/ماذا/كم/متى)، وله إجابة صحيحة واحدة فقط بحسب النص.
- ممنوع: ظهور الإجابة أو جزء منها داخل نص السؤال، أو سؤال غامض أو يحتمل أكثر من إجابة، أو أسئلة رأي وتأويل.
- 4 اختيارات مختلفة تمامًا في المعنى، قصيرة ومتجانسة (كلها أسماء، أو كلها أماكن، أو كلها أرقام...). المشتتات معقولة لكنها خاطئة بوضوح بحسب النص.
- answer: رقم الاختيار الصحيح (0-3) ووزّع مواضع الإجابة الصحيحة. explanation: جملة قصيرة من النص. evidence: نقل حرفي من نص الحدث يثبت الإجابة."""

S_INTRO = {"type": "object", "additionalProperties": False, "required": ["intro", "conclusion"],
           "properties": {"intro": {"type": "string"}, "conclusion": {"type": "string"}}}
S_LQ = {"type": "object", "additionalProperties": False, "required": ["lessons", "quiz"], "properties": {
    "lessons": {"type": "array", "items": {"type": "object", "additionalProperties": False,
        "required": ["title", "text", "event_id", "evidence"],
        "properties": {"title": {"type": "string"}, "text": {"type": "string"}, "event_id": {"type": "integer"}, "evidence": {"type": "string"}}}},
    "quiz": {"type": "array", "items": {"type": "object", "additionalProperties": False,
        "required": ["q", "options", "answer", "explanation", "event_id", "evidence"],
        "properties": {"q": {"type": "string"}, "options": {"type": "array", "items": {"type": "string"}}, "answer": {"type": "integer"},
                       "explanation": {"type": "string"}, "event_id": {"type": "integer"}, "evidence": {"type": "string"}}}}}}

LQ_OUT, INTRO_OUT, ASK = 2500, 1500, 7
window = deque()
def throttle(est):
    while True:
        now = time.time()
        while window and now - window[0][0] > 60: window.popleft()
        if not window or sum(t for _, t in window) + est <= TPM_BUDGET: return
        time.sleep(max(1, 61 - (now - window[0][0])))

NO_RF = False   # لو الموديل رفض response_format نكمّل من غيره ونستخرج الـJSON من النص

def extract_json(t):
    t = t.strip()
    try: return json.loads(t)
    except Exception: return json.loads(t[t.find("{"): t.rfind("}") + 1])

def call(system, user, schema, name, max_out):
    global NO_RF
    est = (len(system) + len(user)) / CHARS_PER_TOKEN + max_out
    for attempt in range(4):
        try:
            throttle(est)
            strict = MODEL.startswith(SCHEMA_MODELS)
            sysmsg = system if strict else system + "\nأعد الرد بصيغة JSON فقط (بدون أي نص آخر) مطابقة لهذا الـschema:\n" + json.dumps(schema, ensure_ascii=False)
            kw = {}
            if strict: kw["response_format"] = {"type": "json_schema", "json_schema": {"name": name, "schema": schema}}
            elif not NO_RF: kw["response_format"] = {"type": "json_object"}
            if "gpt-oss" in MODEL: kw["extra_body"] = {"reasoning_effort": "low"}
            r = client.chat.completions.create(model=MODEL, temperature=0.3, max_completion_tokens=max_out,
                messages=[{"role": "system", "content": sysmsg}, {"role": "user", "content": user}], **kw)
            window.append((time.time(), r.usage.total_tokens))
            print("   ", name, r.usage.prompt_tokens, "in /", r.usage.completion_tokens, "out")
            return extract_json(r.choices[0].message.content)
        except Exception as ex:
            msg = str(ex); print("   retry", name, attempt, msg[:300])
            body = getattr(ex, "body", None); fg = None
            if isinstance(body, dict): fg = body.get("failed_generation") or (body.get("error") or {}).get("failed_generation")
            if fg:   # الموديل طلّع JSON ناقص حقل؛ نستخرجه ونسيب الفلترة تشيل العناصر الناقصة بدل ما نعيد الطلب
                try: print("    (استرجعت الرد من failed_generation)"); return extract_json(fg)
                except Exception: pass
            if "per day" in msg or "TPD" in msg or "RPD" in msg:
                raise SystemExit("\n[stop] وصلتي للحد اليومي للموديل ده. اللي اتحفظ في data/llm فاضل زي ما هو؛ كمّلي بكرة أو بموديل تاني: --model <اسم>")
            if "model_not_found" in msg or "does not exist" in msg:
                raise SystemExit(f"\n[stop] الموديل «{MODEL}» مش متاح لحسابك. شغّلي:  python 02_generate_llm.py --list-models  وإختاري اسم منها.")
            if not strict and not NO_RF and ("response_format" in msg or "json_object" in msg):
                NO_RF = True; print("   (الموديل مش بيدعم JSON mode، هكمل من غيره)"); continue
            time.sleep(20 * (attempt + 1))

def events_of(ch):
    return [e for s in ch["sections"] for e in s["events"]]

def build_payload(ch):
    evs = events_of(ch)
    for snip in (300, 200, 120, 70, 40, 0):
        text = f"الشابتر: {ch['title']}\n" + "\n".join(json.dumps(llm_view(e, snip), ensure_ascii=False) for e in evs)
        if len(text) / CHARS_PER_TOKEN <= PAYLOAD_BUDGET: return text
    return f"الشابتر: {ch['title']}\n" + "\n".join(f"[{e['id']}] {e['full_title']}" for e in evs)

def cut(t, n):
    if len(t) <= n: return t
    k = t.rfind(".", 0, n)
    return t[: k + 1] if k > n * 0.5 else t[:n]

def sample_events(ch):
    evs = [e for e in events_of(ch) if len(e["details"]) >= 150]
    if len(evs) <= N_SAMPLE: return evs
    step = len(evs) / N_SAMPLE
    return [evs[int(i * step)] for i in range(N_SAMPLE)]

def gen_intro(ch):
    r = call(SYS_INTRO, build_payload(ch), S_INTRO, "intro_outro", INTRO_OUT)
    return {"intro": r["intro"], "conclusion": r["conclusion"]} if r and "intro" in r and "conclusion" in r else {}

def _found(ev, text):
    """الـevidence لازم يكون منقول من النص (بتسامح بسيط مع اختلاف كلمة أو اتنين). '...' بتقسّم الاقتباس لأجزاء."""
    text = norm(text)
    parts = [p for p in (norm(x) for x in re.split(r"\.{2,}|…", str(ev))) if len(p) >= 6]
    if not parts: return False
    for p in parts:   # مجموع الأجزاء المتطابقة (كل جزء >= 4 حروف) لازم يغطي 85% من الاقتباس
        blocks = SequenceMatcher(None, p, text, autojunk=False).get_matching_blocks()
        if sum(b.size for b in blocks if b.size >= 4) < 0.85 * len(p): return False
    return True

def validate_lq(res, shown):
    bad, lessons, quiz, seen, used = Counter(), [], [], set(), set()
    for l in res.get("lessons") or []:
        try:
            eid = l["event_id"]
            if eid not in shown: bad["lesson:event_id"] += 1; continue
            if not _found(l.get("evidence", ""), shown[eid]): bad["lesson:evidence"] += 1; continue
            t = norm(l["title"])
            if t in seen: bad["lesson:dup"] += 1; continue
            seen.add(t); lessons.append({"title": l["title"], "text": l["text"], "event_id": eid})
        except (KeyError, TypeError): bad["lesson:format"] += 1
    for q in res.get("quiz") or []:
        try:
            eid, o, ans = q["event_id"], q["options"], int(q["answer"])
            if eid not in shown: bad["quiz:event_id"] += 1; continue
            if eid in used: bad["quiz:same_event"] += 1; continue
            if len(o) != 4 or not 0 <= ans < 4: bad["quiz:format"] += 1; continue
            if len({norm(x) for x in o}) < 4 or any(not norm(x) for x in o): bad["quiz:dup_options"] += 1; continue
            if not _found(q.get("evidence", ""), shown[eid]): bad["quiz:evidence"] += 1; continue
            c = o[ans]
            if leaks(q["q"], c): bad["quiz:answer_in_question"] += 1; continue
            if any(norm(c) in norm(x) or norm(x) in norm(c) for i, x in enumerate(o) if i != ans): bad["quiz:overlap"] += 1; continue
            used.add(eid); quiz.append({"q": q["q"], "options": o, "answer": ans, "explanation": q.get("explanation", ""), "event_id": eid})
        except (KeyError, TypeError, ValueError): bad["quiz:format"] += 1
    if bad: print("    مرفوض:", dict(bad))
    return {"lessons": lessons[:3], "quiz": quiz[:5]}

def gen_lq(ch):
    sample = sample_events(ch)
    if not sample: return {"lessons": [], "quiz": []}
    shown = {e["id"]: cut(e["details"], SAMPLE_CHARS) for e in sample}
    user = "\n\n".join(f"[id={e['id']}] {e['full_title']}" + (f" ({e['hijri_year']})" if e.get("hijri_year") else "") + f"\n{shown[e['id']]}" for e in sample)
    user += f"\n\nعدد أسئلة الكويز المطلوبة: {min(ASK, len(sample))}."
    r = call(SYS_LQ, user, S_LQ, "lessons_quiz", LQ_OUT)
    return validate_lq(r, shown) if r else {}

def run(cid, redo, min_quiz=0):
    dst = OUT / f"{cid}.json"
    out = json.loads(dst.read_text("utf-8")) if dst.exists() else {}
    if redo or any("event_ids" in l for l in out.get("lessons", [])) or ("quiz" in out and len(out["quiz"]) < min_quiz):   # الصيغة القديمة = تتعاد
        out.pop("lessons", None); out.pop("quiz", None)
    ch = json.loads((ROOT / "data" / "chapters" / f"{cid}.json").read_text("utf-8"))
    changed = False
    if "intro" not in out:
        out.update(gen_intro(ch)); changed = True
    if "lessons" not in out or "quiz" not in out:
        out.update(gen_lq(ch)); changed = True
    if not changed: return print("skip", cid)
    dst.write_text(json.dumps(out, ensure_ascii=False, indent=1), "utf-8")
    missing = [k for k in ("intro", "lessons", "quiz") if k not in out]
    if missing: print("INCOMPLETE", cid, "ناقص:", missing, "- شغّلي تاني وهيكمّل الناقص بس")
    print("saved", cid, "| lessons:", len(out.get("lessons", [])), "| quiz:", len(out.get("quiz", [])))

if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--chapter"); ap.add_argument("--redo", action="store_true"); ap.add_argument("--model"); ap.add_argument("--list-models", action="store_true"); ap.add_argument("--min-quiz", type=int, default=0); a = ap.parse_args()
    if a.list_models:
        for m in sorted(m.id for m in client.models.list().data): print(m)
        raise SystemExit
    if a.model: MODEL = a.model
    if "allam" in MODEL:   # سياق 4K توكن شامل الرد: طلبات أصغر بكتير
        PAYLOAD_BUDGET, N_SAMPLE, SAMPLE_CHARS, LQ_OUT, INTRO_OUT, ASK = 1200, 3, 450, 1300, 500, 4
        print("وضع الموديلات الصغيرة (سياق 4K): أحداث أقل ونص أقصر")
    ids = [a.chapter] if a.chapter else [p["id"] for p in json.loads((ROOT / "data" / "index.json").read_text("utf-8"))]
    for cid in ids: run(cid, a.redo, a.min_quiz)
