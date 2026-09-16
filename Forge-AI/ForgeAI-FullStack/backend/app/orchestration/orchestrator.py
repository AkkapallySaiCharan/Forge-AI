from app.agents.planner import PlannerAgent
from app.agents.developer import DeveloperAgent
from app.agents.tester import TesterAgent
from app.agents.security import SecurityAgent
from app.agents.reviewer import ReviewerAgent
from app.database.database import create_run

class Orchestrator:
    def __init__(self):
        self.planner=PlannerAgent(); self.developer=DeveloperAgent(); self.tester=TesterAgent(); self.security=SecurityAgent(); self.reviewer=ReviewerAgent()

    def execute(self,task,code):
        context={"code":code}
        context["planner"]=self.planner.run(task,context)
        context["plan"]=context["planner"]["plan"]
        context["developer"]=self.developer.run(task,context)
        context["tester"]=self.tester.run(task,context)
        context["security"]=self.security.run(task,context)
        context["reviewer"]=self.reviewer.run(task,context)
        return {"task":task,"status":"completed","agents":[context[x] for x in ["planner","developer","tester","security","reviewer"]],"final_review":context["reviewer"]}

    def persist(self,project_id,task,code,result):
        return create_run(project_id,task,code,result)
