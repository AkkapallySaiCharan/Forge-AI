import ast

def imports(code):
    try: tree=ast.parse(code)
    except SyntaxError: return []
    result=set()
    for n in ast.walk(tree):
        if isinstance(n,ast.Import): result.update(a.name.split(".")[0] for a in n.names)
        elif isinstance(n,ast.ImportFrom) and n.module: result.add(n.module.split(".")[0])
    return sorted(result)
