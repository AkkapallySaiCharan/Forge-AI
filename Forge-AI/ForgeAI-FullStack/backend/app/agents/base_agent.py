from abc import ABC, abstractmethod

class BaseAgent(ABC):
    name = "Agent"
    @abstractmethod
    def run(self, task: str, context: dict) -> dict: ...
