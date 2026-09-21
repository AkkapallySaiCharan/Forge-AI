from fastapi.testclient import TestClient
import forgeai_app

client = TestClient(forgeai_app.app)

def test_health_endpoint():
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "ForgeAI"
    assert "llm_mode" in data

def test_root_endpoint():
    response = client.get("/")
    assert response.status_code == 200
    assert "<!DOCTYPE html>" in response.text
    assert "ForgeAI" in response.text

def test_python_metrics():
    code = """
def add(a, b):
    if a > 0:
        return a + b
    return b
"""
    metrics = forgeai_app.python_metrics(code)
    assert metrics["syntax_ok"] is True
    assert metrics["functions"] == 1
    assert metrics["complexity"] >= 2

def test_security_scan():
    safe_code = "def greet(name): return f'Hello, {name}'"
    assert len(forgeai_app.security_scan(safe_code)) == 0

    vuln_code = "SECRET_KEY = 'supersecretkey123'\neval('1+1')"
    findings = forgeai_app.security_scan(vuln_code)
    assert len(findings) >= 2
    titles = [f["title"] for f in findings]
    assert any("secret" in t.lower() for t in titles)
    assert any("eval" in t.lower() for t in titles)

def test_create_project_and_run():
    # Create project
    proj_resp = client.post("/api/projects", json={
        "name": "Automated Test Project",
        "description": "Integration test project"
    })
    assert proj_resp.status_code == 200
    project_id = proj_resp.json()["id"]

    # Create run
    run_resp = client.post("/api/runs", json={
        "project_id": project_id,
        "task": "Test task for multi-agent system",
        "code": "def example(): return 42",
        "language": "python"
    })
    assert run_resp.status_code == 200
    run_id = run_resp.json()["run_id"]

    # Get run
    get_run_resp = client.get(f"/api/runs/{run_id}")
    assert get_run_resp.status_code == 200
    assert get_run_resp.json()["run"]["id"] == run_id

    # Clean up project
    del_resp = client.delete(f"/api/projects/{project_id}")
    assert del_resp.status_code == 200

