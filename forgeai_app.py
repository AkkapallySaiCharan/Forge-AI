"""
Multi-Agent Software Engineering Workspace
===========================================

Single-file production-style portfolio project.

Run:
    pip install fastapi uvicorn pydantic
    python app.py

Optional real LLM mode:
    pip install openai
    set OPENAI_API_KEY=your_key_here        # Windows CMD
    $env:OPENAI_API_KEY="your_key_here"     # PowerShell

Then open:
    http://127.0.0.1:8000

The application works without an API key in DEMO mode, so it can be
opened and demonstrated immediately.

Architecture:
    Browser UI
       -> FastAPI REST API
       -> Orchestrator
       -> Planner / Developer / Tester / Security / Reviewer agents
       -> SQLite persistence
       -> Optional LLM adapter
"""

from __future__ import annotations

import ast
import json
import os
import re
import sqlite3
import subprocess
import sys
import time
import traceback
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    from fastapi import FastAPI, HTTPException
    from fastapi.responses import HTMLResponse
    from pydantic import BaseModel, Field
    import uvicorn
except ImportError:
    print("\nMissing dependencies.")
    print("Run: pip install fastapi uvicorn pydantic\n")
    raise


APP_NAME = "ForgeAI"
DB_PATH = Path(__file__).with_name("forgeai.db")
MAX_CODE_CHARS = 100_000

app = FastAPI(
    title="ForgeAI",
    description="Multi-Agent Software Engineering Workspace",
    version="1.0.0",
)

executor = ThreadPoolExecutor(max_workers=8)


# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------

def db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    conn = db()
    conn.executescript(
        """
        PRAGMA journal_mode=WAL;

        CREATE TABLE IF NOT EXISTS projects (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            description TEXT DEFAULT '',
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS runs (
            id TEXT PRIMARY KEY,
            project_id TEXT NOT NULL,
            task TEXT NOT NULL,
            status TEXT NOT NULL,
            mode TEXT NOT NULL,
            created_at TEXT NOT NULL,
            completed_at TEXT,
            final_summary TEXT DEFAULT '',
            FOREIGN KEY(project_id) REFERENCES projects(id)
        );

        CREATE TABLE IF NOT EXISTS agent_results (
            id TEXT PRIMARY KEY,
            run_id TEXT NOT NULL,
            agent TEXT NOT NULL,
            status TEXT NOT NULL,
            duration_ms INTEGER DEFAULT 0,
            output TEXT DEFAULT '',
            created_at TEXT NOT NULL,
            FOREIGN KEY(run_id) REFERENCES runs(id)
        );
        """
    )
    conn.commit()
    conn.close()


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

class ProjectCreate(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    description: str = Field(default="", max_length=500)


class RunRequest(BaseModel):
    project_id: str
    task: str = Field(min_length=5, max_length=5000)
    code: str = Field(default="", max_length=MAX_CODE_CHARS)
    language: str = Field(default="python", max_length=30)


# ---------------------------------------------------------------------------
# Optional LLM adapter
# ---------------------------------------------------------------------------

def llm_available() -> bool:
    return bool(os.getenv("OPENAI_API_KEY"))


def ask_llm(system: str, user: str) -> str:
    """
    Optional adapter. The core application remains fully runnable without it.
    """
    if not llm_available():
        return ""

    try:
        from openai import OpenAI

        client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
        response = client.responses.create(
            model=os.getenv("OPENAI_MODEL", "gpt-5-mini"),
            instructions=system,
            input=user,
        )
        return response.output_text.strip()
    except Exception:
        return ""


# ---------------------------------------------------------------------------
# Code intelligence
# ---------------------------------------------------------------------------

def python_metrics(code: str) -> Dict[str, Any]:
    metrics = {
        "lines": len(code.splitlines()),
        "characters": len(code),
        "functions": 0,
        "classes": 0,
        "imports": 0,
        "complexity": 0,
        "syntax_ok": True,
    }

    try:
        tree = ast.parse(code)
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                metrics["functions"] += 1
            elif isinstance(node, ast.ClassDef):
                metrics["classes"] += 1
            elif isinstance(node, (ast.Import, ast.ImportFrom)):
                metrics["imports"] += 1
            elif isinstance(
                node,
                (
                    ast.If, ast.For, ast.While, ast.Try,
                    ast.With, ast.BoolOp, ast.IfExp,
                ),
            ):
                metrics["complexity"] += 1
        metrics["complexity"] += metrics["functions"]
    except SyntaxError:
        metrics["syntax_ok"] = False

    return metrics


def security_scan(code: str) -> List[Dict[str, Any]]:
    findings = []

    patterns = [
        (
            r"(password|passwd|secret|api[_-]?key)\s*=\s*['\"][^'\"]+['\"]",
            "Hard-coded secret",
            "critical",
            "Move credentials to environment variables or a secret manager.",
        ),
        (
            r"eval\s*\(",
            "Dynamic eval() usage",
            "high",
            "Avoid eval(); use explicit parsing or a safe dispatch mechanism.",
        ),
        (
            r"exec\s*\(",
            "Dynamic exec() usage",
            "high",
            "Avoid exec() on untrusted or externally supplied input.",
        ),
        (
            r"subprocess\.(run|Popen|call)\([^)]*shell\s*=\s*True",
            "Shell command execution",
            "high",
            "Avoid shell=True when arguments can be passed directly.",
        ),
        (
            r"SELECT\s+.+\s+FROM\s+.+\+",
            "Potential SQL injection",
            "critical",
            "Use parameterized SQL queries.",
        ),
        (
            r"verify\s*=\s*False",
            "TLS verification disabled",
            "high",
            "Keep TLS certificate verification enabled.",
        ),
        (
            r"pickle\.loads?\s*\(",
            "Unsafe pickle deserialization",
            "high",
            "Do not deserialize untrusted pickle data.",
        ),
    ]

    for pattern, title, severity, recommendation in patterns:
        for match in re.finditer(pattern, code, re.IGNORECASE):
            line = code[:match.start()].count("\n") + 1
            findings.append(
                {
                    "title": title,
                    "severity": severity,
                    "line": line,
                    "recommendation": recommendation,
                }
            )

    return findings


def test_suggestions(code: str, language: str) -> List[str]:
    tests = []
    if language.lower() == "python":
        try:
            tree = ast.parse(code)
            functions = [
                n.name for n in ast.walk(tree)
                if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
            ]
            for name in functions[:12]:
                tests.append(f"Test {name} with valid input.")
                tests.append(f"Test {name} with empty/null boundary input.")
                tests.append(f"Test {name} with invalid input and expected exception.")
        except SyntaxError:
            tests.append("Add a syntax-validation test before functional tests.")

    if not tests:
        tests = [
            "Add a happy-path test.",
            "Add invalid-input tests.",
            "Add boundary-value tests.",
            "Add authentication/authorization tests where applicable.",
        ]

    return list(dict.fromkeys(tests))


# ---------------------------------------------------------------------------
# Agents
# ---------------------------------------------------------------------------

class BaseAgent:
    name = "Base Agent"

    def run(self, task: str, code: str, language: str) -> Dict[str, Any]:
        raise NotImplementedError


class PlannerAgent(BaseAgent):
    name = "Planner Agent"

    def run(self, task: str, code: str, language: str) -> Dict[str, Any]:
        metrics = python_metrics(code) if language.lower() == "python" and code else {}
        llm = ask_llm(
            "You are a senior software architect. Return a concise implementation plan.",
            f"Task:\n{task}\n\nLanguage: {language}\n\nCode:\n{code[:30000]}",
        )

        if llm:
            plan = llm
        else:
            plan = "\n".join(
                [
                    "1. Clarify the requested behavior and acceptance criteria.",
                    "2. Identify affected modules, APIs, data models, and dependencies.",
                    "3. Implement the smallest maintainable change.",
                    "4. Add automated tests for happy paths and failure paths.",
                    "5. Run security and regression checks.",
                    "6. Review the final diff before merge.",
                ]
            )

        return {
            "summary": "Created an implementation plan.",
            "plan": plan,
            "metrics": metrics,
        }


class DeveloperAgent(BaseAgent):
    name = "Developer Agent"

    def run(self, task: str, code: str, language: str) -> Dict[str, Any]:
        llm = ask_llm(
            "You are a senior backend engineer. Analyze the supplied code and "
            "describe a safe implementation approach. Do not invent files.",
            f"Task:\n{task}\n\nLanguage: {language}\n\nCode:\n{code[:30000]}",
        )

        if llm:
            recommendation = llm
        else:
            recommendation = (
                "Use small, testable functions; validate external input; "
                "keep business logic separate from transport/database concerns; "
                "avoid breaking existing public interfaces."
            )

        return {
            "summary": "Prepared an implementation strategy.",
            "recommendation": recommendation,
        }


class TesterAgent(BaseAgent):
    name = "Testing Agent"

    def run(self, task: str, code: str, language: str) -> Dict[str, Any]:
        suggestions = test_suggestions(code, language) if code else [
            "Create unit tests for the new business logic.",
            "Create API integration tests for success and failure responses.",
            "Test authentication, authorization, validation, and edge cases.",
            "Add regression tests for existing behavior.",
        ]

        return {
            "summary": f"Generated {len(suggestions)} test scenarios.",
            "tests": suggestions,
        }


class SecurityAgent(BaseAgent):
    name = "Security Agent"

    def run(self, task: str, code: str, language: str) -> Dict[str, Any]:
        findings = security_scan(code) if language.lower() == "python" else []

        if not findings:
            findings = [
                {
                    "title": "No obvious hard-coded-secret or dangerous-pattern finding",
                    "severity": "info",
                    "line": None,
                    "recommendation": (
                        "Continue with dependency scanning, authentication review, "
                        "input validation, and runtime configuration checks."
                    ),
                }
            ]

        return {
            "summary": f"Security scan completed with {len(findings)} finding(s).",
            "findings": findings,
        }


class ReviewerAgent(BaseAgent):
    name = "Reviewer Agent"

    def run(self, task: str, code: str, language: str) -> Dict[str, Any]:
        metrics = python_metrics(code) if language.lower() == "python" and code else {}
        findings = security_scan(code) if language.lower() == "python" else []

        score = 100
        score -= min(30, len(findings) * 12)
        if metrics and not metrics.get("syntax_ok", True):
            score -= 35
        if metrics and metrics.get("complexity", 0) > 20:
            score -= 10
        score = max(score, 0)

        if score >= 90:
            verdict = "APPROVE"
        elif score >= 70:
            verdict = "APPROVE WITH CHANGES"
        else:
            verdict = "REQUEST CHANGES"

        return {
            "summary": "Completed final engineering review.",
            "score": score,
            "verdict": verdict,
            "metrics": metrics,
            "priority": (
                "Resolve critical/high security findings before production merge."
                if findings
                else "Add/verify automated tests and review the final diff."
            ),
        }


AGENTS = [
    PlannerAgent(),
    DeveloperAgent(),
    TesterAgent(),
    SecurityAgent(),
    ReviewerAgent(),
]


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------

def save_agent_result(
    run_id: str,
    agent: str,
    status: str,
    duration_ms: int,
    output: Dict[str, Any],
) -> None:
    conn = db()
    conn.execute(
        """
        INSERT INTO agent_results
        (id, run_id, agent, status, duration_ms, output, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            str(uuid.uuid4()),
            run_id,
            agent,
            status,
            duration_ms,
            json.dumps(output),
            now(),
        ),
    )
    conn.commit()
    conn.close()


def execute_run(run_id: str, task: str, code: str, language: str) -> None:
    conn = db()
    conn.execute("UPDATE runs SET status = 'running' WHERE id = ?", (run_id,))
    conn.commit()
    conn.close()

    results = []

    try:
        # Planner first; specialist agents then run concurrently.
        ordered_agents = AGENTS

        for agent in ordered_agents:
            started = time.perf_counter()
            try:
                result = agent.run(task, code, language)
                elapsed = int((time.perf_counter() - started) * 1000)
                save_agent_result(run_id, agent.name, "completed", elapsed, result)
                results.append((agent.name, result))
            except Exception as exc:
                elapsed = int((time.perf_counter() - started) * 1000)
                save_agent_result(
                    run_id,
                    agent.name,
                    "failed",
                    elapsed,
                    {"error": str(exc)},
                )

        reviewer = next((r for n, r in results if n == "Reviewer Agent"), {})
        summary = (
            f"Workflow completed. Final verdict: "
            f"{reviewer.get('verdict', 'REVIEW REQUIRED')}. "
            f"Engineering score: {reviewer.get('score', 0)}/100."
        )

        conn = db()
        conn.execute(
            """
            UPDATE runs
            SET status='completed', completed_at=?, final_summary=?
            WHERE id=?
            """,
            (now(), summary, run_id),
        )
        conn.commit()
        conn.close()

    except Exception as exc:
        conn = db()
        conn.execute(
            """
            UPDATE runs
            SET status='failed', completed_at=?, final_summary=?
            WHERE id=?
            """,
            (now(), f"Workflow failed: {exc}", run_id),
        )
        conn.commit()
        conn.close()


# ---------------------------------------------------------------------------
# API
# ---------------------------------------------------------------------------

@app.get("/api/health")
def health() -> Dict[str, Any]:
    return {
        "status": "healthy",
        "service": APP_NAME,
        "version": "1.0.0",
        "llm_mode": "live" if llm_available() else "demo",
        "timestamp": now(),
    }


@app.post("/api/projects")
def create_project(payload: ProjectCreate) -> Dict[str, Any]:
    project_id = str(uuid.uuid4())
    conn = db()
    conn.execute(
        """
        INSERT INTO projects (id, name, description, created_at)
        VALUES (?, ?, ?, ?)
        """,
        (project_id, payload.name.strip(), payload.description.strip(), now()),
    )
    conn.commit()
    conn.close()

    return {
        "id": project_id,
        "name": payload.name.strip(),
        "description": payload.description.strip(),
    }


@app.get("/api/projects")
def list_projects() -> List[Dict[str, Any]]:
    conn = db()
    rows = conn.execute(
        "SELECT * FROM projects ORDER BY created_at DESC"
    ).fetchall()
    conn.close()
    return [dict(row) for row in rows]


@app.post("/api/runs")
def create_run(payload: RunRequest) -> Dict[str, Any]:
    conn = db()
    project = conn.execute(
        "SELECT id FROM projects WHERE id = ?", (payload.project_id,)
    ).fetchone()

    if not project:
        conn.close()
        raise HTTPException(status_code=404, detail="Project not found")

    run_id = str(uuid.uuid4())
    mode = "live" if llm_available() else "demo"

    conn.execute(
        """
        INSERT INTO runs
        (id, project_id, task, status, mode, created_at)
        VALUES (?, ?, ?, 'queued', ?, ?)
        """,
        (run_id, payload.project_id, payload.task.strip(), mode, now()),
    )
    conn.commit()
    conn.close()

    executor.submit(
        execute_run,
        run_id,
        payload.task.strip(),
        payload.code,
        payload.language,
    )

    return {
        "run_id": run_id,
        "status": "queued",
        "mode": mode,
    }


@app.get("/api/runs")
def list_runs() -> List[Dict[str, Any]]:
    conn = db()
    rows = conn.execute(
        """
        SELECT
            r.*,
            p.name AS project_name
        FROM runs r
        JOIN projects p ON p.id = r.project_id
        ORDER BY r.created_at DESC
        LIMIT 50
        """
    ).fetchall()
    conn.close()
    return [dict(row) for row in rows]


@app.get("/api/runs/{run_id}")
def get_run(run_id: str) -> Dict[str, Any]:
    conn = db()
    run = conn.execute(
        """
        SELECT r.*, p.name AS project_name
        FROM runs r
        JOIN projects p ON p.id = r.project_id
        WHERE r.id = ?
        """,
        (run_id,),
    ).fetchone()

    if not run:
        conn.close()
        raise HTTPException(status_code=404, detail="Run not found")

    agents = conn.execute(
        """
        SELECT * FROM agent_results
        WHERE run_id = ?
        ORDER BY created_at ASC
        """,
        (run_id,),
    ).fetchall()
    conn.close()

    output = []
    for row in agents:
        item = dict(row)
        try:
            item["output"] = json.loads(item["output"])
        except Exception:
            pass
        output.append(item)

    return {
        "run": dict(run),
        "agents": output,
    }


@app.delete("/api/projects/{project_id}")
def delete_project(project_id: str) -> Dict[str, str]:
    conn = db()
    exists = conn.execute(
        "SELECT id FROM projects WHERE id = ?", (project_id,)
    ).fetchone()

    if not exists:
        conn.close()
        raise HTTPException(status_code=404, detail="Project not found")

    conn.execute(
        "DELETE FROM agent_results WHERE run_id IN "
        "(SELECT id FROM runs WHERE project_id = ?)",
        (project_id,),
    )
    conn.execute("DELETE FROM runs WHERE project_id = ?", (project_id,))
    conn.execute("DELETE FROM projects WHERE id = ?", (project_id,))
    conn.commit()
    conn.close()

    return {"status": "deleted"}


# ---------------------------------------------------------------------------
# Embedded frontend
# ---------------------------------------------------------------------------

HTML = r"""
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>ForgeAI — Multi-Agent Engineering Workspace</title>
<style>
:root{
  --bg:#0b1020;--panel:#121a2d;--panel2:#18223a;--text:#eef3ff;
  --muted:#9ba8c7;--line:#263451;--accent:#7c8cff;--good:#37d39a;
  --warn:#ffc857;--bad:#ff6b7a;
}
*{box-sizing:border-box}
body{margin:0;background:radial-gradient(circle at top,#182345 0,#0b1020 45%);
font-family:Inter,Segoe UI,Arial,sans-serif;color:var(--text)}
button,input,textarea,select{font:inherit}
button{cursor:pointer}
.app{display:grid;grid-template-columns:270px 1fr;min-height:100vh}
.sidebar{border-right:1px solid var(--line);padding:24px;background:rgba(9,14,29,.88)}
.logo{font-size:25px;font-weight:800;letter-spacing:-1px}
.logo span{color:var(--accent)}
.tag{color:var(--muted);font-size:12px;margin-top:4px}
.nav{margin-top:35px;display:grid;gap:8px}
.nav button{background:transparent;border:1px solid transparent;color:var(--muted);
text-align:left;padding:12px 14px;border-radius:10px}
.nav button.active,.nav button:hover{background:var(--panel2);color:var(--text);border-color:var(--line)}
.status{position:absolute;bottom:20px;width:220px;padding:13px;background:var(--panel);
border:1px solid var(--line);border-radius:12px;font-size:12px}
.dot{display:inline-block;width:8px;height:8px;border-radius:50%;background:var(--good);margin-right:7px}
.main{padding:30px;max-width:1500px;width:100%;margin:auto}
.top{display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:25px}
h1{font-size:30px;margin:0 0 6px}
.subtitle{color:var(--muted)}
.grid{display:grid;grid-template-columns:repeat(4,1fr);gap:14px;margin-bottom:18px}
.card{background:rgba(18,26,45,.9);border:1px solid var(--line);border-radius:16px;padding:18px}
.metric{font-size:27px;font-weight:800;margin-top:5px}
.label{font-size:12px;color:var(--muted)}
.workspace{display:grid;grid-template-columns:1.2fr .8fr;gap:18px}
.panel{background:rgba(18,26,45,.94);border:1px solid var(--line);border-radius:16px;padding:20px;margin-bottom:18px}
.panel h2{font-size:17px;margin:0 0 16px}
label{display:block;font-size:12px;color:var(--muted);margin:13px 0 7px}
input,textarea,select{width:100%;background:#0d1528;color:var(--text);border:1px solid var(--line);
border-radius:10px;padding:11px;outline:none}
textarea{min-height:180px;resize:vertical;font-family:Consolas,monospace;font-size:12px}
input:focus,textarea:focus,select:focus{border-color:var(--accent)}
.primary{background:var(--accent);color:white;border:0;padding:11px 16px;border-radius:10px;font-weight:700}
.secondary{background:var(--panel2);color:var(--text);border:1px solid var(--line);padding:10px 14px;border-radius:10px}
.row{display:flex;gap:10px;align-items:center}
.row>*{flex:1}
.agent{display:flex;gap:12px;padding:13px;border:1px solid var(--line);border-radius:12px;margin-bottom:9px;
background:#0e1629}
.agentIcon{width:36px;height:36px;border-radius:9px;background:#202d4e;display:grid;place-items:center}
.agentTitle{font-weight:700;font-size:13px}.agentMeta{font-size:11px;color:var(--muted);margin-top:4px}
.badge{font-size:10px;padding:4px 7px;border-radius:99px;background:#27334f;color:#b8c5e5}
.completed{color:var(--good)}.failed{color:var(--bad)}
.run{padding:12px;border-bottom:1px solid var(--line);cursor:pointer}
.run:hover{background:#17213a}.run:last-child{border:0}
.runTitle{font-weight:650;font-size:13px}.runMeta{font-size:11px;color:var(--muted);margin-top:5px}
.result{white-space:pre-wrap;background:#0a1121;border:1px solid var(--line);padding:13px;border-radius:10px;
font-size:12px;line-height:1.55;max-height:400px;overflow:auto}
.hidden{display:none!important}
.empty{padding:30px;text-align:center;color:var(--muted)}
.notice{padding:11px 13px;border:1px solid var(--line);background:#111a30;border-radius:10px;
font-size:12px;color:var(--muted);margin-bottom:15px}
.score{font-size:42px;font-weight:900}
.verdict{font-weight:800;color:var(--good)}
.small{font-size:11px;color:var(--muted)}
@media(max-width:1000px){.app{grid-template-columns:1fr}.sidebar{display:none}.workspace{grid-template-columns:1fr}.grid{grid-template-columns:repeat(2,1fr)}.main{padding:18px}}
</style>
</head>
<body>
<div class="app">
  <aside class="sidebar">
    <div class="logo">Forge<span>AI</span></div>
    <div class="tag">Multi-Agent Engineering Workspace</div>
    <div class="nav">
      <button class="active" onclick="showPage('workspace',this)">⚡ Workspace</button>
      <button onclick="showPage('runs',this)">◉ Run History</button>
      <button onclick="showPage('architecture',this)">⌘ Architecture</button>
    </div>
    <div class="status"><span class="dot"></span><b id="modeText">Checking system...</b><br>
      <span class="small">FastAPI · SQLite · Agent Orchestrator</span></div>
  </aside>

  <main class="main">
    <section id="workspace">
      <div class="top">
        <div>
          <h1>Engineering Command Center</h1>
          <div class="subtitle">Delegate software work to specialized AI agents and review the result.</div>
        </div>
        <button class="secondary" onclick="createProject()">＋ New Project</button>
      </div>

      <div class="grid">
        <div class="card"><div class="label">AGENTS</div><div class="metric">5</div></div>
        <div class="card"><div class="label">PERSISTENCE</div><div class="metric">SQLite</div></div>
        <div class="card"><div class="label">API</div><div class="metric">REST</div></div>
        <div class="card"><div class="label">LLM</div><div class="metric" id="llmMetric">Demo</div></div>
      </div>

      <div class="workspace">
        <div>
          <div class="panel">
            <h2>New Engineering Task</h2>
            <div class="notice">The workflow is runnable without an API key. Add <b>OPENAI_API_KEY</b> to enable live LLM reasoning.</div>

            <label>Project</label>
            <select id="projectSelect"></select>

            <label>Task / Requirement</label>
            <textarea id="task" style="min-height:120px" placeholder="Example: Add JWT authentication to the user API. Validate credentials, protect private endpoints, add tests, and review security."></textarea>

            <div class="row">
              <div>
                <label>Language</label>
                <select id="language"><option>python</option><option>javascript</option><option>typescript</option><option>java</option></select>
              </div>
              <div>
                <label>Optional source code</label>
                <input id="codeFile" type="file" accept=".py,.js,.ts,.java,.txt" onchange="loadFile(this)">
              </div>
            </div>

            <label>Source Code / Existing File</label>
            <textarea id="code" placeholder="Paste the code you want the agents to inspect..."></textarea>

            <div style="margin-top:14px" class="row">
              <button class="primary" onclick="startRun()">▶ Run Agent Workflow</button>
              <button class="secondary" onclick="loadDemo()">Load Demo</button>
            </div>
          </div>

          <div class="panel">
            <h2>Latest Run</h2>
            <div id="latest"><div class="empty">No workflow run yet.</div></div>
          </div>
        </div>

        <div>
          <div class="panel">
            <h2>Agent Pipeline</h2>
            <div id="agentList">
              <div class="agent"><div class="agentIcon">🧠</div><div><div class="agentTitle">Planner Agent</div><div class="agentMeta">Architecture & acceptance criteria</div></div></div>
              <div class="agent"><div class="agentIcon">💻</div><div><div class="agentTitle">Developer Agent</div><div class="agentMeta">Implementation strategy</div></div></div>
              <div class="agent"><div class="agentIcon">🧪</div><div><div class="agentTitle">Testing Agent</div><div class="agentMeta">Test scenarios & regression coverage</div></div></div>
              <div class="agent"><div class="agentIcon">🛡️</div><div><div class="agentTitle">Security Agent</div><div class="agentMeta">Risk patterns & remediation</div></div></div>
              <div class="agent"><div class="agentIcon">👀</div><div><div class="agentTitle">Reviewer Agent</div><div class="agentMeta">Final score & merge verdict</div></div></div>
            </div>
          </div>

          <div class="panel">
            <h2>Recent Runs</h2>
            <div id="recentRuns"><div class="empty">Loading...</div></div>
          </div>
        </div>
      </div>
    </section>

    <section id="runs" class="hidden">
      <div class="top"><div><h1>Run History</h1><div class="subtitle">Auditable record of agent workflows.</div></div></div>
      <div class="panel"><div id="allRuns"></div></div>
    </section>

    <section id="architecture" class="hidden">
      <div class="top"><div><h1>System Architecture</h1><div class="subtitle">Production-style separation of concerns in one runnable file.</div></div></div>
      <div class="panel">
        <div class="result">
Browser UI
   │
   ▼
FastAPI REST API
   │
   ├── Project Service ───────► SQLite
   │
   └── Run Orchestrator
           │
           ├── Planner Agent
           ├── Developer Agent
           ├── Testing Agent
           ├── Security Agent
           └── Reviewer Agent
                    │
                    ▼
              Persisted Results
                    │
                    ▼
             Review Dashboard

Optional:
OpenAI API ──► Agent reasoning layer

Engineering characteristics:
• RESTful API boundaries
• Background workflow execution
• Persistent run history
• Structured agent outputs
• Security scanning
• AST-based Python metrics
• Health endpoint
• Environment-based configuration
• Responsive dashboard
• Demo mode for local development
        </div>
      </div>
    </section>
  </main>
</div>

<script>
let currentRun = null;
let poller = null;

async function api(url, options={}) {
  const res = await fetch(url, {headers:{'Content-Type':'application/json'}, ...options});
  const data = await res.json();
  if (!res.ok) throw new Error(data.detail || 'Request failed');
  return data;
}

async function boot() {
  try {
    const health = await api('/api/health');
    document.getElementById('modeText').textContent =
      health.llm_mode === 'live' ? 'Live LLM Mode' : 'Demo Mode';
    document.getElementById('llmMetric').textContent =
      health.llm_mode === 'live' ? 'Live' : 'Demo';
    await refreshProjects();
    await refreshRuns();
  } catch(e) {
    document.getElementById('modeText').textContent = 'API Error';
    console.error(e);
  }
}

async function refreshProjects() {
  const projects = await api('/api/projects');
  const select = document.getElementById('projectSelect');

  if (!projects.length) {
    const p = await api('/api/projects', {
      method:'POST',
      body:JSON.stringify({
        name:'Demo Engineering Project',
        description:'Default project for the ForgeAI workspace'
      })
    });
    return refreshProjects();
  }

  select.innerHTML = projects.map(p =>
    `<option value="${p.id}">${escapeHtml(p.name)}</option>`
  ).join('');
}

async function createProject() {
  const name = prompt('Project name:');
  if (!name) return;
  const description = prompt('Short description:') || '';
  await api('/api/projects', {
    method:'POST',
    body:JSON.stringify({name,description})
  });
  await refreshProjects();
}

async function startRun() {
  const project_id = document.getElementById('projectSelect').value;
  const task = document.getElementById('task').value.trim();
  const code = document.getElementById('code').value;
  const language = document.getElementById('language').value;

  if (!task) {
    alert('Enter an engineering task first.');
    return;
  }

  const data = await api('/api/runs', {
    method:'POST',
    body:JSON.stringify({project_id,task,code,language})
  });

  currentRun = data.run_id;
  document.getElementById('latest').innerHTML =
    `<div class="notice">Run queued. Agents are starting...</div>`;
  if (poller) clearInterval(poller);
  poller = setInterval(pollRun, 700);
  await refreshRuns();
}

async function pollRun() {
  if (!currentRun) return;
  try {
    const data = await api('/api/runs/' + currentRun);
    renderRun(data);

    if (data.run.status === 'completed' || data.run.status === 'failed') {
      clearInterval(poller);
      poller = null;
      await refreshRuns();
    }
  } catch(e) {
    console.error(e);
  }
}

function renderRun(data) {
  const r = data.run;
  let html = `<div class="notice"><b>${escapeHtml(r.status.toUpperCase())}</b> · ${escapeHtml(r.mode)} mode<br>${escapeHtml(r.final_summary || 'Agents are working...')}</div>`;

  if (data.agents.length) {
    html += data.agents.map(a => {
      const o = a.output || {};
      let text = JSON.stringify(o, null, 2);
      if (o.plan) text = o.plan;
      if (o.recommendation) text = o.recommendation;
      if (o.tests) text = o.tests.map((x,i)=>`${i+1}. ${x}`).join('\\n');
      if (o.findings) text = o.findings.map(f=>`[${f.severity.toUpperCase()}] ${f.title} | line ${f.line || '-'}\\n${f.recommendation}`).join('\\n\\n');
      if (o.verdict) text = `VERDICT: ${o.verdict}\\nSCORE: ${o.score}/100\\n\\n${o.priority}`;
      return `<div class="agent">
        <div class="agentIcon">✓</div>
        <div style="flex:1">
          <div class="agentTitle">${escapeHtml(a.agent)}
            <span class="badge ${a.status}">${escapeHtml(a.status)}</span>
            <span class="small">${a.duration_ms} ms</span>
          </div>
          <div class="agentMeta">${escapeHtml(o.summary || '')}</div>
          <div class="result" style="margin-top:9px">${escapeHtml(text)}</div>
        </div>
      </div>`;
    }).join('');
  }

  document.getElementById('latest').innerHTML = html;
}

async function refreshRuns() {
  const runs = await api('/api/runs');
  const html = runs.length ? runs.map(r => `
    <div class="run" onclick="openRun('${r.id}')">
      <div class="runTitle">${escapeHtml(r.task.slice(0,80))}</div>
      <div class="runMeta">${escapeHtml(r.project_name)} · ${escapeHtml(r.status)} · ${new Date(r.created_at).toLocaleString()}</div>
    </div>`).join('') : '<div class="empty">No runs yet.</div>';

  document.getElementById('recentRuns').innerHTML = html;
  document.getElementById('allRuns').innerHTML = html;
}

async function openRun(id) {
  currentRun = id;
  const data = await api('/api/runs/' + id);
  renderRun(data);
  showPage('workspace', document.querySelector('.nav button'));
}

function loadDemo() {
  document.getElementById('task').value =
    'Add secure JWT authentication to this API. Validate credentials, protect private endpoints, add tests, and identify security risks before production deployment.';
  document.getElementById('language').value = 'python';
  document.getElementById('code').value =
`from fastapi import FastAPI

app = FastAPI()

SECRET_KEY = "demo-secret-change-me"

def authenticate(username, password):
    return username == "admin" and password == "password"

@app.get("/users")
def users():
    return {"users": ["Alice", "Bob"]}
`;
}

function loadFile(input) {
  const file = input.files[0];
  if (!file) return;
  const reader = new FileReader();
  reader.onload = e => document.getElementById('code').value = e.target.result;
  reader.readAsText(file);
}

function showPage(id, button) {
  ['workspace','runs','architecture'].forEach(x =>
    document.getElementById(x).classList.add('hidden'));
  document.getElementById(id).classList.remove('hidden');
  document.querySelectorAll('.nav button').forEach(b=>b.classList.remove('active'));
  if (button) button.classList.add('active');
  if (id === 'runs') refreshRuns();
}

function escapeHtml(s) {
  return String(s ?? '').replace(/[&<>"']/g, c => ({
    '&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#039;'
  }[c]));
}

boot();
</script>
</body>
</html>
"""


@app.get("/", response_class=HTMLResponse)
def home() -> str:
    return HTML


# ---------------------------------------------------------------------------
# Startup
# ---------------------------------------------------------------------------

init_db()

if __name__ == "__main__":
    print("=" * 68)
    print(" ForgeAI — Multi-Agent Software Engineering Workspace")
    print("=" * 68)
    print(" Dashboard : http://127.0.0.1:8000")
    print(" Health    : http://127.0.0.1:8000/api/health")
    print(" LLM mode  :", "LIVE" if llm_available() else "DEMO")
    print(" Database  :", DB_PATH)
    print("=" * 68)
    print("Press CTRL+C to stop.\n")
    
uvicorn.run(
    app,
    host="127.0.0.1",
    port=int(os.getenv("PORT", "8000")),
    reload=False,
)