"""
Career Intelligence MCP Server
"""

import asyncio
from pathlib import Path

import faiss
import numpy as np
import ollama
import pdfplumber
import requests
from bs4 import BeautifulSoup
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import (
    CallToolResult,
    ListToolsResult,
    TextContent,
    Tool,
)
from sentence_transformers import SentenceTransformer

# ─────────────────────────────────────────────
# GLOBAL STATE
# ─────────────────────────────────────────────

resume_context: str = ""
knowledge_chunks: list[str] = []
faiss_index = None
embedder = SentenceTransformer("all-MiniLM-L6-v2")

# ─────────────────────────────────────────────
# RAG HELPERS
# ─────────────────────────────────────────────

def load_knowledge(file_path: str) -> str:
    global knowledge_chunks, faiss_index
    text = Path(file_path).read_text(encoding="utf-8")
    knowledge_chunks = [c.strip() for c in text.split("\n\n") if c.strip()]
    embeddings = embedder.encode(knowledge_chunks)
    faiss_index = faiss.IndexFlatL2(embeddings.shape[1])
    faiss_index.add(np.array(embeddings))
    return f"Loaded {len(knowledge_chunks)} knowledge chunks."


def retrieve_context(query: str, top_k: int = 3) -> str:
    if faiss_index is None or not knowledge_chunks:
        return ""
    query_vector = embedder.encode([query])
    _, indices = faiss_index.search(np.array(query_vector), top_k)
    return "\n".join(knowledge_chunks[i] for i in indices[0] if i < len(knowledge_chunks))


# ─────────────────────────────────────────────
# RESUME LOADER
# ─────────────────────────────────────────────

def load_resume(file_path: str) -> str:
    global resume_context
    with pdfplumber.open(file_path) as pdf:
        text = "\n".join(page.extract_text() or "" for page in pdf.pages)
    resume_context = text.strip()
    return f"Resume loaded ({len(resume_context)} chars)."


# ─────────────────────────────────────────────
# BASE AGENT
# ─────────────────────────────────────────────

class BaseAgent:
    def __init__(self, role_prompt: str):
        self.role_prompt = role_prompt

    def run(self, user_input: str, shared_context: str = "") -> str:
        knowledge = retrieve_context(user_input)
        messages = [
            {"role": "system", "content": self.role_prompt},
            {"role": "system", "content": f"User Resume:\n{resume_context}"},
            {"role": "system", "content": f"Relevant Knowledge:\n{knowledge}"},
        ]
        if shared_context:
            messages.append({
                "role": "system",
                "content": f"Previous Analysis:\n{shared_context}",
            })
        messages.append({"role": "user", "content": user_input})
        response = ollama.chat(model="llama3", messages=messages)
        return response["message"]["content"]


# ─────────────────────────────────────────────
# AGENTS
# ─────────────────────────────────────────────

resume_agent   = BaseAgent("You are a Resume Analysis Agent. Analyze strengths and weaknesses. Return bullet points.")
skill_gap_agent= BaseAgent("You are a Skill Gap Agent. Identify missing skills for next career level. Be specific.")
roadmap_agent  = BaseAgent("You are a Roadmap Agent. Create a 6-month structured career roadmap with monthly milestones.")
salary_agent   = BaseAgent("You are a Salary Strategy Agent. Suggest practical strategies to increase compensation.")
interview_agent= BaseAgent("You are an Interview Preparation Agent. Suggest a prep plan, key topics, and mock strategy.")


# ─────────────────────────────────────────────
# ORCHESTRATOR
# ─────────────────────────────────────────────

def orchestrator(user_input: str) -> str:
    shared = ""
    r1 = resume_agent.run(user_input);            shared += f"\nRESUME:\n{r1}\n"
    r2 = skill_gap_agent.run(user_input, shared); shared += f"\nSKILL GAPS:\n{r2}\n"
    r3 = roadmap_agent.run(user_input, shared);   shared += f"\nROADMAP:\n{r3}\n"
    r4 = salary_agent.run(user_input, shared);    shared += f"\nSALARY:\n{r4}\n"
    r5 = interview_agent.run(user_input, shared)
    return f"""
================ CAREER INTELLIGENCE REPORT ================
RESUME ANALYSIS:\n{r1}
SKILL GAPS:\n{r2}
ROADMAP:\n{r3}
SALARY STRATEGY:\n{r4}
INTERVIEW PLAN:\n{r5}
============================================================
"""


# ─────────────────────────────────────────────
# MCP SERVER  — fixed handler signatures
# ─────────────────────────────────────────────

server = Server("career-intelligence")

TOOLS = [
    Tool(name="load_resume",        description="Load a PDF resume.",
         inputSchema={"type":"object","properties":{"file_path":{"type":"string"}},"required":["file_path"]}),
    Tool(name="load_knowledge",     description="Index a plain-text knowledge base.",
         inputSchema={"type":"object","properties":{"file_path":{"type":"string"}},"required":["file_path"]}),
    Tool(name="analyze_resume",     description="Analyze resume strengths and weaknesses.",
         inputSchema={"type":"object","properties":{"query":{"type":"string"}},"required":["query"]}),
    Tool(name="skill_gap",          description="Identify missing skills.",
         inputSchema={"type":"object","properties":{"query":{"type":"string"},"shared_context":{"type":"string","default":""}},"required":["query"]}),
    Tool(name="roadmap",            description="Generate a 6-month career roadmap.",
         inputSchema={"type":"object","properties":{"query":{"type":"string"},"shared_context":{"type":"string","default":""}},"required":["query"]}),
    Tool(name="salary_strategy",    description="Get compensation strategies.",
         inputSchema={"type":"object","properties":{"query":{"type":"string"},"shared_context":{"type":"string","default":""}},"required":["query"]}),
    Tool(name="interview_prep",     description="Get an interview preparation plan.",
         inputSchema={"type":"object","properties":{"query":{"type":"string"},"shared_context":{"type":"string","default":""}},"required":["query"]}),
    Tool(name="full_career_report", description="Run all agents and return a full report.",
         inputSchema={"type":"object","properties":{"query":{"type":"string"}},"required":["query"]}),
    Tool(name="fetch_job",          description="Fetch a LinkedIn job description from a URL.",
         inputSchema={"type":"object","properties":{"url":{"type":"string"}},"required":["url"]}),
]


# ── KEY FIX: handlers take only (request) not (self, request) ────────────────

@server.list_tools()
async def handle_list_tools() -> ListToolsResult:          # ← no extra arg
    return ListToolsResult(tools=TOOLS)


@server.call_tool()
async def handle_call_tool(name: str, arguments: dict) -> list[TextContent]:  # ← name + arguments directly
    args = arguments or {}
    try:
        if name == "load_resume":
            result = load_resume(args["file_path"])
        elif name == "load_knowledge":
            result = load_knowledge(args["file_path"])
        elif name == "analyze_resume":
            result = resume_agent.run(args["query"])
        elif name == "skill_gap":
            result = skill_gap_agent.run(args["query"], args.get("shared_context", ""))
        elif name == "roadmap":
            result = roadmap_agent.run(args["query"], args.get("shared_context", ""))
        elif name == "salary_strategy":
            result = salary_agent.run(args["query"], args.get("shared_context", ""))
        elif name == "interview_prep":
            result = interview_agent.run(args["query"], args.get("shared_context", ""))
        elif name == "full_career_report":
            result = orchestrator(args["query"])
        elif name == "fetch_job":
            headers = {"User-Agent": "Mozilla/5.0"}
            resp = requests.get(args["url"], headers=headers, timeout=10)
            result = BeautifulSoup(resp.text, "html.parser").get_text()[:2000]
        else:
            result = f"Unknown tool: {name}"
    except Exception as exc:
        result = f"Error in '{name}': {exc}"

    return [TextContent(type="text", text=result)]


# ─────────────────────────────────────────────
# ENTRY POINT
# ─────────────────────────────────────────────

async def main():
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())

if __name__ == "__main__":
    asyncio.run(main())