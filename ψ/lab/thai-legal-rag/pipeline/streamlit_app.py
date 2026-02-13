#!/usr/bin/env python3
"""
Thai Legal RAG — Streamlit launcher

Usage:
    streamlit run pipeline/streamlit_app.py
    (from the thai-legal-rag/ directory)
"""
import subprocess
import sys
from pathlib import Path

app_path = Path(__file__).parent.parent / "app" / "streamlit_app.py"

if __name__ == "__main__":
    # When called directly (python pipeline/streamlit_app.py), relaunch via streamlit
    subprocess.run(
        ["streamlit", "run", str(app_path)] + sys.argv[1:],
        check=True,
    )
else:
    # When called via `streamlit run pipeline/streamlit_app.py`,
    # Streamlit imports this as a module — just exec the real app.
    exec(app_path.read_text(encoding="utf-8"), {"__file__": str(app_path)})
