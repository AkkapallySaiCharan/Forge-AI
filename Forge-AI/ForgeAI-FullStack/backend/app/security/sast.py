import re
RULES=[("eval",r"\beval\s*\(","Dynamic execution detected."),("exec",r"\bexec\s*\(","Dynamic execution detected."),("shell=True",r"shell\s*=\s*True","Potential command injection."),("verify=False",r"verify\s*=\s*False","TLS verification disabled."),("pickle.loads",r"pickle\.loads\s*\(","Unsafe deserialization.")]

def scan(code):
    return [{"rule":n,"severity":"high","message":m} for n,p,m in RULES if re.search(p,code,re.I)]
