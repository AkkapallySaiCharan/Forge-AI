from app.agents.base_agent import BaseAgent
class TesterAgent(BaseAgent):
    name="Testing Agent"
    def run(self,task,context):
        return {"agent":self.name,"status":"completed","summary":"Test strategy generated.","scenarios":["Happy path","Invalid input","Boundary values","Dependency failure","Regression behavior","Authorization/security bypass"],"coverage_targets":["unit","integration","negative","security"]}
