from app.agents.base_agent import BaseAgent
class PlannerAgent(BaseAgent):
    name="Planner Agent"
    def run(self,task,context):
        return {"agent":self.name,"status":"completed","summary":"Requirement decomposed into engineering steps.","plan":[
            "Understand requirements and acceptance criteria.",
            "Inspect affected architecture and dependencies.",
            "Design API, business logic and data changes.",
            "Implement the smallest maintainable change.",
            "Create unit, integration and negative tests.",
            "Perform security and quality review."
        ]}
