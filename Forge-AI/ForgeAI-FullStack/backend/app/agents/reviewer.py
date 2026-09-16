from app.agents.base_agent import BaseAgent
class ReviewerAgent(BaseAgent):
    name="Reviewer Agent"
    def run(self,task,context):
        findings=context.get("security",{}).get("findings",[])
        score=max(0,10-min(len(findings)*2,8))
        return {"agent":self.name,"status":"completed","score":score,"verdict":"CHANGES_REQUESTED" if findings else "APPROVE","summary":"Final engineering review completed.","recommendations":["Resolve security findings before merge."] if findings else ["Keep tests and CI checks updated."]}
