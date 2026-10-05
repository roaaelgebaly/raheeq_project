# الرحيق المختوم — Reader

## التشغيل
```bash
pip install -r requirements.txt

# 1) CSV -> JSON لكل شابتر (بدون LLM) + أسئلة من الداتا
cd pipeline && python 01_build_chapters.py

# 2) (اختياري) — انسخي .env.example إلى .env وحطي المفتاح مقدمة/خاتمة/دروس/Quiz بالـLLM — جربي شابتر واحد الأول
python 02_generate_llm.py --chapter ch01

# 3) الباك
cd backend && uvicorn main:app --reload      # :8000

# 4) الفرونت
cd frontend && npm install && npm run dev    # :5173
```

## تجربة دراسة الفصل
كل حدث يظهر في شاشة مستقلة. عند بدء الفصل يمكن اختيار التحقق الاختياري بعد الأحداث، ثم عرض الدروس والعبر وحل اختبار الفصل؛ ويمكن تخطي هذه الخطوات أو الانتقال إلى الفصل التالي.
التحقق يطلب من القارئ تلخيص أهم ما فهمه، والـLLM بيتنادى فقط لما تضغطي "تحقق من فهمي" (`POST /api/check`).
محتاجة `GROQ_API_KEY` في `.env` (الباك بيقراه). الحالة بتتخزن في `localStorage` تحت `raheeq:ls`.
