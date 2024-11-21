import streamlit.web.cli as stcli
import sys
from pathlib import Path

if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).parent / "src"))
    sys.argv = ["streamlit", "run", "src/app.py"]
    sys.exit(stcli.main()) 