#!/usr/bin/env python3
"""EasyDoc launcher — run without installing:
    python run.py compress big.pdf -o small.pdf --target-mb 5
    python run.py gui
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "gui":
        from easydoc import gui
        gui.main()
    else:
        from easydoc import cli
        raise SystemExit(cli.main())
