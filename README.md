# AI Career Mentor

> Multi-Agent AI career advisor powered by **MCP (Model Context Protocol)**, **RAG (FAISS)**, **Ollama / llama3**, FastAPI, and React.

---

## Project Structure

```
ai-career-mentor/
├── backend/
│   ├── app.py                  # FastAPI server — MCP client
│   ├── career_mcp_server.py    # MCP server — all 5 agents live here
│   ├── requirements.txt
│   └── data/                   # create this folder
│       ├── resume.pdf          # your resume (auto-loaded on startup)
│       └── knowledge.txt       # RAG knowledge base
│
├── frontend/
│   ├── src/
│   │   └── App.js
│   └── package.json
│
└── README.md
```

---

## Architecture

```
React UI (frontend/)          FastAPI (backend/app.py)       MCP Server (backend/career_mcp_server.py)
  localhost:3000     ─HTTP──▶  MCP Client  ─stdio──▶  subprocess  ──▶  5 Agents + RAG + Ollama
```

`app.py` and `career_mcp_server.py` live in the same `backend/` folder.  
`app.py` spawns `career_mcp_server.py` as a subprocess and talks to it over the MCP stdio protocol (JSON-RPC 2.0).  
The React `package.json` has `"proxy": "http://localhost:8000"` so the frontend calls `/ask` — not `http://localhost:8000/ask`.

---

## Prerequisites

| Tool | Version | Install |
|------|---------|---------|
| Python | 3.10+ | [python.org](https://python.org) |
| Node.js | 18+ | [nodejs.org](https://nodejs.org) |
| Ollama | latest | [ollama.ai](https://ollama.ai) |

---

## Setup & Run

### 1 — Clone

```bash
git clone https://github.com/anwesha999/ai-career-mentor
cd ai-career-mentor
```

### 2 — Backend

```bash
cd backend
pip install -r requirements.txt
```

Pull the local LLM (one-time, ~4 GB):
```bash
ollama pull llama3
ollama serve          # keep this running in a terminal
```

Put your files in `backend/data/`:
```
backend/data/resume.pdf
backend/data/knowledge.txt
```

Start the API:
```bash
# from the backend/ folder
uvicorn app:app --reload --port 8000
```

On startup, the API auto-loads your resume and knowledge base. You'll see:
```
Resume loaded from .../backend/data/resume.pdf
Knowledge loaded from .../backend/data/knowledge.txt
```

Verify:
```bash
curl http://localhost:8000/
# → {"status": "Career Intelligence API is running"}

curl http://localhost:8000/tools
# → {"tools": ["load_resume", "analyze_resume", "skill_gap", ...]}
```

### 3 — Frontend

```bash
cd frontend
npm install
npm start
```

Opens at [http://localhost:3000](http://localhost:3000).

---

## Manual file loading (if not using data/ folder)

```bash
curl -X POST http://localhost:8000/load/resume \
  -H "Content-Type: application/json" \
  -d '{"file_path": "/absolute/path/to/resume.pdf"}'

curl -X POST http://localhost:8000/load/knowledge \
  -H "Content-Type: application/json" \
  -d '{"file_path": "/absolute/path/to/knowledge.txt"}'
```

---

## API Reference

| Method | Endpoint | Body | Description |
|--------|----------|------|-------------|
| GET | `/` | — | Health check |
| GET | `/tools` | — | List MCP tools |
| POST | `/load/resume` | `{"file_path": "..."}` | Load PDF resume |
| POST | `/load/knowledge` | `{"file_path": "..."}` | Index knowledge base |
| POST | `/ask` | `{"query": "...", "mode": "..."}` | Run an agent |

### Mode values for `/ask`

| mode | Agent called |
|------|-------------|
| `full` | Orchestrator (all 5 agents in sequence) |
| `resume` | Resume analysis |
| `skills` | Skill gap analysis |
| `roadmap` | 6-month career roadmap |
| `salary` | Salary strategy |
| `interview` | Interview preparation |

### Example

```bash
curl -X POST http://localhost:8000/ask \
  -H "Content-Type: application/json" \
  -d '{"query": "I want to become Staff Engineer at a top AI company", "mode": "full"}'
```

---

## Claude Desktop integration

Add to `~/Library/Application Support/Claude/claude_desktop_config.json` (Mac):

```json
{
  "mcpServers": {
    "ai-career-mentor": {
      "command": "/path/to/python3",
      "args": ["/path/to/ai-career-mentor/backend/career_mcp_server.py"]
    }
  }
}
```

Find your python path: `which python3`  
Find your project path: `pwd` inside the `backend/` folder.

---

## Common Issues

### `ImportError: cannot import name 'orchestrator'`
You have the stub version of `career_mcp_server.py`. Replace it with the full version from this repo.

### `handle_call_tool() takes 1 positional argument but 2 were given`
MCP SDK v1.x changed handler signatures. Use:
```python
@server.call_tool()
async def handle_call_tool(name: str, arguments: dict) -> list[TextContent]:
```

### `stdio_client() missing 1 required positional argument: 'server'`
Pass `StdioServerParameters` to `stdio_client()`:
```python
from mcp.client.stdio import stdio_client, StdioServerParameters
params = StdioServerParameters(command=sys.executable, args=["career_mcp_server.py"])
async with stdio_client(params) as (read, write):
```

### `npm error: Could not read package.json`
Run `npm install` and `npm start` from the `frontend/` folder, not from the project root.

### `ollama: connection refused`
Run `ollama serve` in a separate terminal first.

### Resume not persisting between requests
Place your files in `backend/data/` — they auto-load on startup via the `@app.on_event("startup")` hook.

---

## Running order

Open 3 terminals:

```bash
# Terminal 1 — Ollama
ollama serve

# Terminal 2 — Backend
cd ai-career-mentor/backend
uvicorn app:app --reload --port 8000

# Terminal 3 — Frontend
cd ai-career-mentor/frontend
npm start
```

---

## Stack

| Layer | Technology |
|-------|-----------|
| Frontend | React 18 |
| Backend | FastAPI + uvicorn |
| AI protocol | MCP (Model Context Protocol) |
| LLM | Ollama / llama3 (local) |
| RAG | FAISS + SentenceTransformers |
| PDF parsing | pdfplumber |

---

*Built by Anwesha Sinha*