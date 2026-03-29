# Career Intelligence — Setup Guide

## Your file structure should look like this:

```
PythonProject/               ← your existing PyCharm project
├── app.py                   ← FastAPI backend  (replace with new version)
├── career_mcp_server.py     ← MCP + Agents     (keep as-is)
├── knowledge.txt            ← RAG knowledge base
└── AnweshaSinha_Resumes.pdf ← your resume

career-ui/                   ← NEW React app (create this)
└── src/
    └── App.js               ← replace with new version
```

---

## Step 1 — Fix the backend (inside PythonProject)

Replace `app.py` with the new version, then restart uvicorn:

```bash
cd /Users/anweshasinha/PycharmProjects/PythonProject
uvicorn app:app --reload
```

Test it works:
```bash
curl http://localhost:8000/
# → {"status":"Career Intelligence API is running 🚀"}
```

---

## Step 2 — Load resume + knowledge on startup (one-time)

In a separate terminal (while uvicorn is running):

```bash
curl -X POST http://localhost:8000/load/resume \
  -H "Content-Type: application/json" \
  -d '{"file_path": "/Users/anweshasinha/PycharmProjects/PythonProject/AnweshaSinha_Resumes.pdf"}'

curl -X POST http://localhost:8000/load/knowledge \
  -H "Content-Type: application/json" \
  -d '{"file_path": "/Users/anweshasinha/PycharmProjects/PythonProject/knowledge.txt"}'
```

---

## Step 3 — Create the React app (do this ONCE)

```bash
# Go somewhere outside PythonProject (e.g. your home folder or Desktop)
cd ~
npx create-react-app career-ui
cd career-ui

# Replace the default App.js with the new one
cp /path/to/new/App.js src/App.js

# Start React
npm start
```

React will open at http://localhost:3000
Backend runs at http://localhost:8000

---

## Step 4 — Use it!

1. Open http://localhost:3000
2. Pick a mode (Full Report, Resume Analysis, Skill Gaps, etc.)
3. Type your career question and press Enter or click Ask

---

## Running order every time you work on this:

| Terminal | Command |
|----------|---------|
| Terminal 1 | `cd PythonProject && uvicorn app:app --reload` |
| Terminal 2 | `cd career-ui && npm start` |
