from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[4]
root_str = str(ROOT)
if sys.path[0] != root_str:
    if root_str in sys.path:
        sys.path.remove(root_str)
    sys.path.insert(0, root_str)
