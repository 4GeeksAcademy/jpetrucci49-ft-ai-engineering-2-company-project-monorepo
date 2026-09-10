from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
for path in (_ROOT, _ROOT / "services", _ROOT / "services" / "api"):
    text = str(path)
    if text not in sys.path:
        sys.path.insert(0, text)
