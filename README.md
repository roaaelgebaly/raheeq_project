# Al-Raheeq Al-Makhtum — Interactive Reader

An interactive reading and learning application for *Ar-Raheeq Al-Makhtum (The Sealed Nectar)*, designed to provide a structured, chapter-by-chapter reading experience with optional comprehension checks, key lessons, and AI-powered quizzes.

---

## Features

- **Chapter-Based Reading:** Read the book chapter by chapter, with each event displayed on a dedicated screen.
- **Structured Content:** Convert CSV source data into organized JSON files for individual chapters without requiring an LLM.
- **Optional Comprehension Checks:** Choose whether to enable comprehension checks when starting a chapter.
- **AI-Powered Understanding Assessment:** Summarize what you have learned and receive AI-powered feedback.
- **Lessons & Insights:** Explore key lessons and takeaways from each chapter.
- **Chapter Quizzes:** Test your understanding through chapter-specific quizzes generated from the source data.
- **Flexible Learning Flow:** Skip optional activities or proceed directly to the next chapter.
- **Progress Persistence:** Save reading progress and learning state locally using browser `localStorage`.

---

## Tech Stack

- **Frontend:** JavaScript / Node.js
- **Backend:** Python / FastAPI
- **Data Processing:** Python, CSV, JSON
- **AI Integration:** Groq API
- **State Persistence:** Browser Local Storage

---

## Getting Started

### Prerequisites

Make sure you have the following installed:

- Python 3.10+
- Node.js and npm
- pip

**Note:** A Groq API key is only required for optional LLM-powered features.

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Build Chapter Data

Convert the source CSV files into structured JSON files for each chapter.

This step does **not** require an LLM or an API key.

```bash
cd pipeline
python 01_build_chapters.py
```

The script also generates chapter-specific quiz questions directly from the source data.

### 3. Generate AI-Powered Content (Optional)

Copy the example environment file:

```bash
cp .env.example .env
```

Add your Groq API key to `.env`:

```env
GROQ_API_KEY=your_groq_api_key
```

Generate AI-powered content for a specific chapter:

```bash
python 02_generate_llm.py --chapter ch01
```

**Tip:** Start with a single chapter (`ch01`) to test the integration before generating content for additional chapters.

LLM-generated content may include:

- Chapter introductions
- Chapter conclusions
- Lessons and reflections
- Additional quiz content

### 4. Run the Backend

Open a terminal and navigate to the backend directory:

```bash
cd backend
uvicorn main:app --reload
```

Backend URL:

```text
http://localhost:8000
```

### 5. Run the Frontend

Open a separate terminal:

```bash
cd frontend
npm install
npm run dev
```

Frontend URL:

```text
http://localhost:5173
```

---

## 📚 Reading Experience

Each chapter follows a guided learning flow:

1. **Start a Chapter:** Select a chapter and choose whether to enable optional comprehension checks.
2. **Read the Events:** Each event appears on a separate screen for a focused reading experience.
3. **Check Your Understanding (Optional):** Summarize the most important points you have learned.
4. **Receive AI Feedback:** Submit your summary to receive an AI-powered assessment.
5. **Explore Lessons:** Review the lessons and insights associated with the chapter.
6. **Take the Chapter Quiz:** Test your knowledge through chapter-specific questions.
7. **Continue Reading:** Skip optional activities or move directly to the next chapter.

---

## AI-Powered Comprehension Assessment

The LLM is called **only when the reader explicitly clicks "Check My Understanding."**

This triggers the following API endpoint:

```http
POST /api/check
```

This design ensures:

- No unnecessary LLM requests.
- Better control over API usage.
- An optional AI-assisted learning experience.
- Core reading functionality remains independent of the LLM.

---

## Progress Persistence

The application stores reading progress and learning state locally in the browser using `localStorage`.

**Storage Key:**

```text
raheeq:ls
```

This allows readers to retain their progress across page reloads in the same browser.

---

## Project Structure

```text
.
├── pipeline/
│   ├── 01_build_chapters.py
│   └── 02_generate_llm.py
│
├── backend/
│   └── main.py
│
├── frontend/
│   └── ...
│
├── requirements.txt
└── .env.example
```

---

## Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `GROQ_API_KEY` | API key for LLM-powered features | Optional |

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/check` | Evaluates the reader's understanding of chapter content |

---

## Design Principles

- **Reader-First Experience:** Provide a focused and distraction-free reading environment.
- **Optional AI Integration:** Keep core reading and data processing independent of LLM services.
- **Efficient API Usage:** Trigger AI assessment only through explicit user interaction.
- **Flexible Learning:** Let readers control their learning flow and skip optional activities.
- **Local Progress Tracking:** Preserve reading state without requiring user accounts.

---

## License

Add your preferred license before distributing or publishing the project.

---

**Al-Raheeq Al-Makhtum — An interactive way to read, reflect, and learn.**
