"""PyTeXLogs 测试不允许 import pytexmk。"""
from __future__ import annotations
import sys
assert "pytexmk" not in sys.modules, "pytexmk must NOT be imported in PyTeXLogs tests"
class _BlockPyTeXMKFinder:
    def find_spec(self, fullname, path=None, target=None):
        if fullname == "pytexmk" or fullname.startswith("pytexmk."):
            raise ImportError("PyTeXLogs tests MUST NOT import pytexmk (violation: %s)." % fullname)
        return None
sys.meta_path.insert(0, _BlockPyTeXMKFinder())
