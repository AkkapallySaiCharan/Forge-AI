import os, httpx

class GitHubService:
    def __init__(self): self.token=os.getenv("GITHUB_TOKEN")
    def repository(self,owner,repo):
        if not self.token: return {"enabled":False,"message":"Configure GITHUB_TOKEN first."}
        r=httpx.get(f"https://api.github.com/repos/{owner}/{repo}",headers={"Authorization":f"Bearer {self.token}"},timeout=15)
        r.raise_for_status()
        return r.json()
