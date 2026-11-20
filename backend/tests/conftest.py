import os
import tempfile

# app.main creates its default application on import; keep test imports self-contained.
os.environ.setdefault("DATABASE_URL", f"sqlite:///{tempfile.gettempdir()}/relay_import_test.db")
os.environ["LLM_API_KEYS"] = ""
