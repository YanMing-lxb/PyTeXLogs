import re
import sys
from pathlib import Path

# -----------------------------------------------------------------------
# <<<<<<<<<<<<<<<<<<<<<<<<<<| 项目配置 |>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
# -----------------------------------------------------------------------

__team__ = "YanMing"
PROJECT_NAME = "pytexlogs"
ROOT_DIR = Path(__file__).parent.parent
SRC_DIR = ROOT_DIR / "src" / "pytexlogs"
SRCPYD_DIR = ROOT_DIR / "srcpyd"
TOOLS_DIR = ROOT_DIR / "tools"
SRC_ENTRY_POINT = SRC_DIR / "__init__.py"
VENV_NAME = ".venv"
if sys.platform == "win32":
    ICON_FILE = TOOLS_DIR / "icon.ico"
elif sys.platform == "darwin":
    ICON_FILE = TOOLS_DIR / "icon.icns"
else:
    ICON_FILE = TOOLS_DIR / "icon.png"


def _read_version():
    version_file = SRC_DIR / "version.py"
    match = re.search(r'__version__\s*=\s*["\']([^"\']+)["\']', version_file.read_text(encoding="utf-8"))
    if match:
        return match.group(1)
    raise RuntimeError(f"无法从 {version_file} 中解析 __version__")


__version__ = _read_version()

__all__ = [
    "ICON_FILE",
    "PROJECT_NAME",
    "ROOT_DIR",
    "SRC_DIR",
    "SRC_ENTRY_POINT",
    "SRCPYD_DIR",
    "TOOLS_DIR",
    "VENV_NAME",
    "__team__",
    "__version__",
]
