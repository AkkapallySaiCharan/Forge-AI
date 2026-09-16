from app.orchestration.orchestrator import Orchestrator

def test_all_agents_run():
    result=Orchestrator().execute("Add authentication","")
    assert len(result["agents"])==5
    assert result["final_review"]["verdict"]=="APPROVE"
