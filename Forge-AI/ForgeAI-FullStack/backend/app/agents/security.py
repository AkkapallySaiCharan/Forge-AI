from app.agents.base_agent import BaseAgent
from app.security.sast import scan
from app.security.secrets import find_secrets
class SecurityAgent(BaseAgent):
    name="Security Agent"
    def run(self,task,context):
        findings=scan(context.get("code",""))+find_secrets(context.get("code",""))
        return {"agent":self.name,"status":"completed","risk":"HIGH" if findings else "LOW","findings":findings}
