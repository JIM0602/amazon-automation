from src.api.main import app

for r in app.routes:
    if hasattr(r, "path"):
        if "monitor" in r.path.lower() or "cost" in r.path.lower():
            methods = getattr(r, "methods", set())
            print(f"  {methods} {r.path}")
