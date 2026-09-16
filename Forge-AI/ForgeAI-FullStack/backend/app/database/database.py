import json, sqlite3
from datetime import datetime, timezone
from pathlib import Path

DB = Path(__file__).resolve().parents[2] / "forgeai.db"

def connect():
    db = sqlite3.connect(DB)
    db.row_factory = sqlite3.Row
    return db

def init_db():
    with connect() as db:
        db.execute("CREATE TABLE IF NOT EXISTS projects (id INTEGER PRIMARY KEY AUTOINCREMENT,name TEXT NOT NULL,description TEXT NOT NULL,repository_url TEXT,created_at TEXT NOT NULL)")
        db.execute("CREATE TABLE IF NOT EXISTS runs (id INTEGER PRIMARY KEY AUTOINCREMENT,project_id INTEGER NOT NULL,task TEXT NOT NULL,code TEXT NOT NULL,status TEXT NOT NULL,result TEXT NOT NULL,created_at TEXT NOT NULL)")
        db.commit()

init_db()

def database_status():
    try:
        with connect() as db: db.execute("SELECT 1")
        return "connected"
    except Exception: return "error"

def create_project(name, description, repository_url):
    now = datetime.now(timezone.utc)
    with connect() as db:
        cur = db.execute("INSERT INTO projects(name,description,repository_url,created_at) VALUES(?,?,?,?)",(name,description,repository_url,now.isoformat()))
        db.commit()
    return {"id":cur.lastrowid,"name":name,"description":description,"repository_url":repository_url,"created_at":now}

def project_exists(project_id):
    with connect() as db: return db.execute("SELECT 1 FROM projects WHERE id=?",(project_id,)).fetchone() is not None

def get_projects():
    with connect() as db: rows=db.execute("SELECT * FROM projects ORDER BY id DESC").fetchall()
    return [{**dict(r),"created_at":datetime.fromisoformat(r["created_at"])} for r in rows]

def remove_project(project_id):
    with connect() as db:
        db.execute("DELETE FROM runs WHERE project_id=?",(project_id,))
        cur=db.execute("DELETE FROM projects WHERE id=?",(project_id,))
        db.commit()
        return cur.rowcount > 0

def create_run(project_id,task,code,result):
    now=datetime.now(timezone.utc)
    with connect() as db:
        cur=db.execute("INSERT INTO runs(project_id,task,code,status,result,created_at) VALUES(?,?,?,?,?,?)",(project_id,task,code,result["status"],json.dumps(result),now.isoformat()))
        db.commit()
    return {"id":cur.lastrowid,"project_id":project_id,"task":task,"status":result["status"],"result":result,"created_at":now}

def get_runs():
    with connect() as db: rows=db.execute("SELECT * FROM runs ORDER BY id DESC").fetchall()
    return [{"id":r["id"],"project_id":r["project_id"],"task":r["task"],"status":r["status"],"result":json.loads(r["result"]),"created_at":datetime.fromisoformat(r["created_at"])} for r in rows]

def get_run(run_id):
    with connect() as db: r=db.execute("SELECT * FROM runs WHERE id=?",(run_id,)).fetchone()
    if not r: return None
    return {"id":r["id"],"project_id":r["project_id"],"task":r["task"],"status":r["status"],"result":json.loads(r["result"]),"created_at":datetime.fromisoformat(r["created_at"])}
