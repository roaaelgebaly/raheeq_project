import { useEffect, useRef, useState } from "react";

const get = (u) => fetch(u).then((r) => r.json());

function useReveal() {
  const ref = useRef();
  useEffect(() => {
    const o = new IntersectionObserver(([e]) => e.isIntersecting && (ref.current.classList.add("in"), o.disconnect()), { threshold: 0.1 });
    o.observe(ref.current); return () => o.disconnect();
  }, []);
  return ref;
}

function EventCard({ e }) {
  const ref = useReveal();
  const [orig, setOrig] = useState(false);
  const text = e.story && !orig ? e.story : e.details;
  const chips = [
    e.hijri_year && `${e.hijri_year}${e.month ? " · " + e.month : ""}`,
    e.gregorian_year && `${e.gregorian_approx ? "نحو " : ""}${e.gregorian_year} م`,
    e.nubuwwa_year && `سنة ${e.nubuwwa_year} من النبوة`,
    e.place && `📍 ${e.place}`,
  ].filter(Boolean);
  return (
    <article id={`ev-${e.id}`} ref={ref} className="event reveal">
      <span className="dot" />
      <h3>{e.title}</h3>
      <div className="chips">{chips.map((c) => <span key={c}>{c}</span>)}
        {e.date_needs_review && <span className="warn">التاريخ تقريبي</span>}</div>
      {text.split(/\n+/).map((t, i) => <p key={i}>{t}</p>)}
      {e.lesson && <div className="lesson-box">💡 <b>عبرة:</b> {e.lesson}</div>}
      <small>الرحيق المختوم، ص {e.page}</small>
      {e.story && <button className="link" onClick={() => setOrig(!orig)}>{orig ? "عرض الصياغة القصصية" : "عرض النص الأصلي"}</button>}
    </article>
  );
}

function Quiz({ quiz, onComplete }) {
  const [i, setI] = useState(0), [pick, setPick] = useState(null), [score, setScore] = useState(0);
  if (!quiz.length) return null;
  if (i >= quiz.length) return <section className="box"><h2>اختبر نفسك</h2><p>نتيجتك: {score} من {quiz.length}</p><button onClick={() => { setI(0); setScore(0); setPick(null); }}>إعادة</button><button className="go" onClick={onComplete}>إنهاء الفصل</button></section>;
  const q = quiz[i];
  const choose = (k) => { if (pick !== null) return; setPick(k); if (k === q.answer) setScore(score + 1); };
  return (
    <section className="box">
      <h2>اختبر نفسك <small>({i + 1}/{quiz.length})</small></h2>
      <p className="q">{q.q}</p>
      {q.options.map((o, k) => (
        <button key={k} onClick={() => choose(k)} className={"opt " + (pick === null ? "" : k === q.answer ? "ok" : k === pick ? "bad" : "")}>{o}</button>
      ))}
      {pick !== null && <>
        <p className="expl">{q.explanation} <a href={`#ev-${q.event_id}`}>اذهب للحدث</a></p>
        <button onClick={() => { setI(i + 1); setPick(null); }}>التالي</button></>}
    </section>
  );
}

const ICON = { good: "✓", partial: "~", needs_review: "!" };

function Check({ ev, saved, onSave, onContinue }) {
  const [ans, setAns] = useState(""), [st, setSt] = useState("idle"), [res, setRes] = useState(null);
  const submit = async () => {
    setSt("loading");
    try {
      const r = await fetch("/api/check", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ event_id: ev.id, user_answer: ans }) });
      if (!r.ok) throw new Error();
      const d = await r.json();
      setRes(d); setSt("result");
      onSave(ev.id, { event_id: ev.id, understanding_level: d.understanding_level, missing_concepts: [...d.missing, ...d.misunderstood] });
    } catch { setSt("error"); }
  };
  return (
    <div className="check">
      {st === "idle" && <>
        <h4>اختبر المعلومات التي فهمتها</h4>
        <p>عبّر بكلماتك عن أهم شيء فهمته من هذا الحدث.</p>
        <textarea value={ans} maxLength={600} rows={3} onChange={(e) => setAns(e.target.value)} />
        <button className="go" disabled={!ans.trim()} onClick={submit}>تحقق من فهمي</button>
        {saved && <small className="saved-check">{ICON[saved.understanding_level]} سبق أن تحققت من فهم هذا الحدث.</small>}
        <button onClick={onContinue}>تخطي</button></>}
      {st === "loading" && <p>جارٍ التحقق…</p>}
      {st === "error" && <><p>تعذر التحقق من إجابتك الآن، يمكنك متابعة الرحلة.</p>
        <button onClick={() => setSt("idle")}>حاول مرة أخرى</button><button className="go" onClick={onContinue}>تابع</button></>}
      {st === "result" && <>
        <p><b>{{ good: "ممتاز! 👏 فهمت الفكرة الأساسية.", partial: "أحسنت، بقيت نقطة صغيرة للمراجعة.", needs_review: "يبدو أن هناك نقطة تحتاج إلى مراجعة بسيطة قبل أن نكمل." }[res.understanding_level]}</b> {res.feedback}</p>
        {res.review_snippets.length > 0 && <div className="snip"><small>من نص الحدث:</small>{res.review_snippets.map((t, i) => <blockquote key={i}>{t}</blockquote>)}</div>}
        <button className="go" onClick={onContinue}>{{ good: "التالي", partial: "فهمت الآن، نكمل", needs_review: "نكمل" }[res.understanding_level]}</button></>}
    </div>
  );
}

function Chapter({ id, onBack, next, onNext }) {
  const [ch, setCh] = useState(null);
  const [stage, setStage] = useState("event"), [eventIndex, setEventIndex] = useState(0);
  const [ls, setLs] = useState(() => { try { return JSON.parse(localStorage.getItem("raheeq:ls") || "{}"); } catch { return {}; } });   // Learning State
  const save = (eid, v) => setLs((o) => { const n = { ...o, [eid]: v }; try { localStorage.setItem("raheeq:ls", JSON.stringify(n)); } catch {} return n; });
  useEffect(() => { setCh(null); setStage("event"); setEventIndex(0); get(`/api/chapters/${id}`).then(setCh); window.scrollTo(0, 0); }, [id]);
  if (!ch) return <p className="center">جارٍ التحميل…</p>;
  const all = ch.sections.flatMap((s) => s.events);
  const event = all[eventIndex];
  const quiz = ch.quiz || [];
  const lessons = ch.lessons || [];
  const canCheck = Boolean(event && typeof event.details === "string" && event.details.length <= 5500);
  const progress = Math.round((eventIndex / Math.max(all.length, 1)) * 100);
  const scrollTop = () => window.scrollTo(0, 0);
  const showAfterEvents = () => {
    setStage(lessons.length ? "lessons" : quiz.length ? "quiz" : "complete");
    scrollTop();
  };
  const advanceEvent = () => {
    if (eventIndex + 1 < all.length) {
      setEventIndex(eventIndex + 1);
      setStage("event");
    } else {
      showAfterEvents();
      return;
    }
    scrollTop();
  };
  const previousEvent = () => {
    if (eventIndex === 0) return;
    setEventIndex(eventIndex - 1);
    setStage("event");
    scrollTop();
  };
  const continueFromCheck = () => eventIndex + 1 < all.length ? advanceEvent() : showAfterEvents();
  const section = ch.sections.find((s) => s.events.some((e) => e.id === event?.id));
  return (
    <>
      <div className="progress" style={{ width: progress + "%" }} />
      <header className="hero chapter-heading"><button className="link" onClick={onBack}>← الفصول</button><h1>{ch.title}</h1></header>
      {stage === "event" && event && <main className="timeline flow-screen">
        <div className="chapter-actions" aria-label="خيارات الفصل">
          {lessons.length > 0 && <button onClick={() => { setStage("lessons"); scrollTop(); }}>دروس وعبر من الفصل</button>}
          {quiz.length > 0 && <button onClick={() => { setStage("quiz"); scrollTop(); }}>اختبار الفصل كاملًا</button>}
        </div>
        {eventIndex === 0 && ch.intro && <p className="intro">{ch.intro}</p>}
        {section?.title && <h2 className="sec">{section.title}</h2>}
        <EventCard e={event} />
        <p className="event-counter">الحدث {eventIndex + 1} من {all.length}</p>
        <div className="flow-actions event-actions">
          {eventIndex > 0 && <button onClick={previousEvent}>الحدث السابق</button>}
          {canCheck && <button onClick={() => { setStage("check"); scrollTop(); }}>اختبر فهم هذا الحدث</button>}
          <button className="go" onClick={advanceEvent}>
            {eventIndex + 1 < all.length ? "الحدث التالي" : "إنهاء الأحداث"}
          </button>
        </div>
      </main>}
      {stage === "check" && event && <main className="box flow-screen">
        <div className="chapter-actions" aria-label="خيارات الفصل">
          {lessons.length > 0 && <button onClick={() => { setStage("lessons"); scrollTop(); }}>دروس وعبر من الفصل</button>}
          {quiz.length > 0 && <button onClick={() => { setStage("quiz"); scrollTop(); }}>اختبار الفصل كاملًا</button>}
        </div>
        <p className="event-counter">تلخيص الحدث {eventIndex + 1} من {all.length}</p>
        <Check key={event.id} ev={event} saved={ls[event.id]} onSave={save} onContinue={continueFromCheck} />
        <div className="flow-actions event-actions">
          {eventIndex > 0 && <button onClick={previousEvent}>الحدث السابق</button>}
          <button onClick={() => { setStage("event"); scrollTop(); }}>العودة إلى الحدث</button>
        </div>
      </main>}
      {stage === "lessons" && <main className="box flow-screen">
        <h2>دروس وعبر</h2>
        {ch.conclusion && <p className="intro">{ch.conclusion}</p>}
        {lessons.map((l, i) => <div key={i} className="lesson"><p><b>{l.title}</b> — {l.text}</p>
          {l.event_id && <small>من الحدث: {all.find((e) => e.id === l.event_id)?.title || ""}</small>}</div>)}
        <div className="flow-actions">
          {eventIndex > 0 && <button onClick={previousEvent}>الحدث السابق</button>}
          <button onClick={() => { setStage("event"); scrollTop(); }}>العودة إلى الحدث</button>
          {quiz.length > 0 && <button className="go" onClick={() => { setStage("quiz"); scrollTop(); }}>اختبار الفصل كاملًا</button>}
          <button onClick={() => { setStage("complete"); scrollTop(); }}>إنهاء الفصل</button>
        </div>
      </main>}
      {stage === "quiz" && <main className="flow-screen">
        <Quiz quiz={quiz} onComplete={() => { setStage("complete"); scrollTop(); }} />
        <div className="box center">
          {eventIndex > 0 && <button onClick={previousEvent}>الحدث السابق</button>}
          <button onClick={() => { setStage("event"); scrollTop(); }}>العودة إلى الحدث</button>
          <button onClick={() => { setStage("complete"); scrollTop(); }}>تخطي الاختبار</button>
        </div>
      </main>}
      {stage === "complete" && <main className="box flow-screen center">
        <h2>أحسنت! أتممت الفصل</h2>
        {next ? <button className="go" onClick={onNext}>الفصل التالي: {next.title} ←</button> : <button className="go" onClick={onBack}>العودة إلى الفصول</button>}
      </main>}
    </>
  );
}

export default function App() {
  const [list, setList] = useState([]), [cur, setCur] = useState(null);
  const [theme, setTheme] = useState("light"), [size, setSize] = useState(20);
  useEffect(() => { get("/api/chapters").then(setList); }, []);
  return (
    <div className={`app ${theme}`} style={{ fontSize: size }}>
      <div className="tools">
        {["light", "sepia", "dark"].map((t) => <button key={t} onClick={() => setTheme(t)}>{{ light: "فاتح", sepia: "سيبيا", dark: "داكن" }[t]}</button>)}
        <button onClick={() => setSize(size + 2)}>أ+</button><button onClick={() => setSize(size - 2)}>أ-</button>
      </div>
      {cur ? <Chapter id={cur} onBack={() => setCur(null)} next={list[list.findIndex((c) => c.id === cur) + 1]} onNext={() => setCur(list[list.findIndex((c) => c.id === cur) + 1].id)} /> : (
        <main className="list"><h1>الرحيق المختوم</h1>
          {list.map((c, i) => <button key={c.id} className="card" onClick={() => setCur(c.id)}><b>{i + 1}</b><span>{c.title}</span><small>{c.n_events} حدث</small></button>)}
        </main>)}
    </div>
  );
}
