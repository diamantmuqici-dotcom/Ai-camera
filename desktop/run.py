"""PyInstaller entry point; also works as `python run.py` from desktop/."""
from claritycam.__main__ import main

if __name__ == "__main__":
    raise SystemExit(main())
