import re
PATTERNS=[("AWS key",r"\bAKIA[0-9A-Z]{16}\b"),("API key",r"(?i)(api[_-]?key|secret[_-]?key)\s*=\s*['\"][^'\"]{12,}['\"]"),("Password",r"(?i)password\s*=\s*['\"][^'\"]{6,}['\"]")]

def find_secrets(code):
    return [{"rule":n,"severity":"high","message":"Potential hard-coded secret detected."} for n,p in PATTERNS if re.search(p,code)]
