"""CSV -> data/chapters/chNN.json (بدون LLM). الداتا الأصلية بترتيبها زي ما هي + أسئلة quiz من الداتا."""
import json, random
from itertools import groupby
from pathlib import Path
import pandas as pd
from cleaning import clean_text, leaks

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "chapters"; OUT.mkdir(parents=True, exist_ok=True)
random.seed(7)
nn = lambda v: None if pd.isna(v) else v

def event(r):
    return {
        "id": int(r.event_id),
        "title": nn(r.subsection) or nn(r.section) or r.title,
        "full_title": r.title, "subsection": nn(r.subsection),
        "details": clean_text(r.details),
        "hijri_year": nn(r.hijri_year), "month": nn(r.lunar_month),
        "gregorian_year": None if pd.isna(r.gregorian_year) else int(r.gregorian_year),
        "gregorian_approx": r.gregorian_basis == "mid_year_estimate",
        "nubuwwa_year": None if pd.isna(r.nubuwwa_year) else int(r.nubuwwa_year),
        "place": nn(r.location_name), "place_from_text": r.location_basis == "text",
        "date_needs_review": bool(r.needs_review),
        "page": int(r.printed_page_start),
    }

def mcq(q, correct, pool, ev_id, expl):
    wrong = [p for p in set(pool) if p != correct]
    if len(wrong) < 3: return None
    opts = random.sample(wrong, 3) + [correct]; random.shuffle(opts)
    return {"q": q, "options": opts, "answer": opts.index(correct), "explanation": expl, "event_id": ev_id}

def data_quiz(events, all_places):
    qs = []
    for e in events:
        if e["place"] and e["place_from_text"]:
            if leaks(f"أين وقع حدث «{e['title']}»؟", e["place"]): continue   # الإجابة ظاهرة في السؤال
            m = mcq(f"أين وقع حدث «{e['title']}»؟", e["place"], all_places, e["id"], f"ذُكر المكان في هذا الحدث: {e['place']}.")
            if m: qs.append(m)
    random.shuffle(qs); return qs[:3]

df = pd.read_csv(ROOT / "data" / "raheeq_events_with_sources.csv")
df = df.dropna(subset=["chapter"]).sort_values("event_id")   # زي النوتبوك: dropna على chapter
places = df.location_name.dropna().unique().tolist()
index = []
for i, (name, g) in enumerate(df.groupby("chapter", sort=False), 1):
    cid = f"ch{i:02d}"
    evs = [event(r) for r in g.itertuples()]
    secs = [{"title": nn(k), "events": [event(r) for r in grp]}
            for k, grp in groupby(g.itertuples(), key=lambda r: nn(r.section))]
    ch = {"id": cid, "title": name, "n_events": len(evs), "sections": secs, "quiz_data": data_quiz(evs, places)}
    (OUT / f"{cid}.json").write_text(json.dumps(ch, ensure_ascii=False, indent=1), "utf-8")
    index.append({"id": cid, "title": name, "n_events": len(evs), "words": int(g.word_count.sum())})
(ROOT / "data" / "index.json").write_text(json.dumps(index, ensure_ascii=False, indent=1), "utf-8")
print(f"{len(index)} chapters, {len(df)} events")
