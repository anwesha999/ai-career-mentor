from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import sys
import os

from mcp import ClientSession
from mcp.client.stdio import stdio_client, StdioServerParameters

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Paths — both files live in backend/ together ─────────────────────────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MCP_SERVER_PATH = os.path.join(BASE_DIR, "career_mcp_server.py")
PYTHON_PATH = sys.executable  # same Python that runs app.py

# ── Request models ────────────────────────────────────────────────────────────

class Query(BaseModel):
    query: str
    mode: str = "full"   # full | resume | skills | roadmap | salary | interview

class LoadRequest(BaseModel):
    file_path: str

# ── Core MCP caller ───────────────────────────────────────────────────────────

async def call_mcp_tool(tool_name: str, args: dict) -> str:
    server_params = StdioServerParameters(
        command=PYTHON_PATH,
        args=[MCP_SERVER_PATH],
        env=None
    )
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool(tool_name, arguments=args)
            return result.content[0].text

# ── Startup: pre-load resume + knowledge so they persist ─────────────────────
# Edit these paths to point to your actual files.
# They can be absolute paths or relative to the backend/ folder.

RESUME_PATH    = os.path.join(BASE_DIR, "data", "resume.pdf")
KNOWLEDGE_PATH = os.path.join(BASE_DIR, "data", "knowledge.txt")

@app.on_event("startup")
async def startup():
    if os.path.exists(RESUME_PATH):
        await call_mcp_tool("load_resume", {"file_path": RESUME_PATH})
        print(f"Resume loaded from {RESUME_PATH}")
    else:
        print(f"[warn] Resume not found at {RESUME_PATH} — call /load/resume manually")

    if os.path.exists(KNOWLEDGE_PATH):
        await call_mcp_tool("load_knowledge", {"file_path": KNOWLEDGE_PATH})
        print(f"Knowledge loaded from {KNOWLEDGE_PATH}")
    else:
        print(f"[warn] Knowledge not found at {KNOWLEDGE_PATH} — call /load/knowledge manually")

# ── Routes ────────────────────────────────────────────────────────────────────

@app.get("/")
def root():
    return {"status": "Career Intelligence API is running"}

@app.get("/tools")
async def list_tools():
    """List all tools the MCP server exposes."""
    server_params = StdioServerParameters(command=PYTHON_PATH, args=[MCP_SERVER_PATH])
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = await session.list_tools()
            return {"tools": [t.name for t in tools.tools]}

@app.post("/load/resume")
async def api_load_resume(req: LoadRequest):
    result = await call_mcp_tool("load_resume", {"file_path": req.file_path})
    return {"message": result}

@app.post("/load/knowledge")
async def api_load_knowledge(req: LoadRequest):
    result = await call_mcp_tool("load_knowledge", {"file_path": req.file_path})
    return {"message": result}

@app.post("/ask")
async def ask(q: Query):
    tool_map = {
        "resume":    "analyze_resume",
        "skills":    "skill_gap",
        "roadmap":   "roadmap",
        "salary":    "salary_strategy",
        "interview": "interview_prep",
        "full":      "full_career_report",
    }
    tool = tool_map.get(q.mode, "full_career_report")
    try:
        result = await call_mcp_tool(tool, {"query": q.query})
        return {"answer": result}
    except Exception as e:
        return {"answer": f"Error: {str(e)}"}