import os

class LLMService:
    def __init__(self):
        self.key=os.getenv("OPENAI_API_KEY")
        self.model=os.getenv("OPENAI_MODEL","gpt-5-mini")
    def status(self):
        return {"enabled":bool(self.key),"mode":"LLM" if self.key else "DEMO","model":self.model if self.key else None}
