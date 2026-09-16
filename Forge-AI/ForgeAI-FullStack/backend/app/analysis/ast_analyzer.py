import ast

def analyze_python(code):
    try: tree=ast.parse(code)
    except SyntaxError as e: return {"valid":False,"error":str(e)}
    return {"valid":True,"lines":len(code.splitlines()),"functions":sum(isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef)) for n in ast.walk(tree)),"classes":sum(isinstance(n,ast.ClassDef) for n in ast.walk(tree)),"imports":sum(isinstance(n,(ast.Import,ast.ImportFrom)) for n in ast.walk(tree))}
