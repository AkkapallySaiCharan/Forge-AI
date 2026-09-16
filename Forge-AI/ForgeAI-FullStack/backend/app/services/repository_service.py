from pathlib import Path

class RepositoryService:
    def inspect(self,path):
        root=Path(path)
        if not root.exists(): raise FileNotFoundError(path)
        files=[str(p.relative_to(root)) for p in root.rglob("*") if p.is_file() and ".git" not in p.parts and "__pycache__" not in p.parts]
        return {"file_count":len(files),"files":files[:500]}
