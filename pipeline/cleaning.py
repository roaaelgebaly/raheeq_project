"""منطق الاختيار والتنضيف من نوتبوك «الرحيق المختوم» (خلايا clean_event و NARRATIVE_FIELDS)."""
import re

def clean_text(t: str) -> str:
    t = re.sub(r"\s+", " ", str(t)).strip()
    t = re.sub(r"\s+([،؛:.!؟])", r"\1", t)
    return t

# نفس الأعمدة اللي كان clean_event في النوتبوك بيبعتها للـLLM (والباقي: IDs/صفحات/QA بيتشال)
LLM_FIELDS = ["full_title", "subsection", "details", "hijri_year", "month",
              "gregorian_year", "nubuwwa_year", "place"]

def llm_view(e: dict, snip: int | None = None) -> dict:
    """زي clean_event: الحقول المسموحة بس، والقيم الفاضية بتتشال. snip = قص details لتصغير الحجم."""
    d = {"id": e["id"]}
    for k in LLM_FIELDS:
        v = e.get(k)
        if v is not None and str(v).strip():
            if k == "subsection" and str(v) in str(e.get("full_title", "")): continue  # مكرر داخل العنوان
            d[k] = v
    if snip is not None:
        if snip: d["details"] = d["details"][:snip]
        else: d.pop("details", None)
    if e.get("gregorian_approx") or e.get("date_needs_review"):
        d["date_note"] = "تقريبي/غير مؤكد"   # عشان الـLLM ما يحوّله لتاريخ قاطع
    return d


# ---------- أدوات التحقق من الـQuiz والدروس ----------
_DIAC = re.compile(r"[\u064B-\u0652\u0670\u0640]")

def norm(t) -> str:
    """تطبيع عربي للمقارنة: بدون تشكيل/تطويل/علامات، وتوحيد الألف والياء والتاء المربوطة."""
    t = _DIAC.sub("", str(t))
    t = re.sub(r"[أإآٱ]", "ا", t).replace("ى", "ي").replace("ة", "ه")
    t = re.sub(r"[^\w\s]", " ", t)
    return re.sub(r"\s+", " ", t).strip()

def _words(t):
    return [re.sub(r"^ال", "", w) for w in norm(t).split()]

def leaks(question: str, answer: str) -> bool:
    """True لو الإجابة (أو كلمة مهمة منها) ظاهرة في نص السؤال نفسه."""
    qw = set(_words(question))
    return any((len(w) >= 3 or w.isdigit()) and w in qw for w in _words(answer))
