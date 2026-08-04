import io, json, sys
from pathlib import Path
from pytexlogs.cli import main as _M
_S = Path(__file__).resolve().parent.parent / "tests/fixtures/sample.log"
def _R(a):
    o,e = io.StringIO(),io.StringIO()
    x,y = sys.stdout,sys.stderr
    sys.stdout,sys.stderr = o,e
    try: r = _M(a)
    finally: sys.stdout,sys.stderr = x,y
    return r,o.getvalue(),e.getvalue()

def test_a():
    c,o,e = _R(["--version"])
    assert c == 0 and "pytexlogs" in o
def test_b():
    c,o,e = _R(["--help"])
    assert c == 0 and all(x in o for x in ["check","summary","export","demo"])
def test_c():
    c,o,e = _R(["check", str(_S)])
    assert c == 1
def test_d():
    c,o,e = _R(["summary", str(_S)])
    assert c == 0
def test_e():
    c,o,e = _R(["summary","--lang","en", str(_S)])
    assert c == 0 and len(o) > 0
def test_f():
    c,o,e = _R(["export","--format","json", str(_S)])
    assert c in (0, 2)
def test_g():
    c,o,e = _R(["export","--format","csv", str(_S)])
    assert c == 0 and "file,line,level" in o[:120]
def test_h():
    c,o,e = _R(["export","--format","sarif", str(_S)])
    assert c == 0
    d = json.loads(o)
    assert '$schema' in d
    assert d["runs"][0]["tool"]["driver"]["name"] == "pytexlogs"
def test_i():
    c,o,e = _R(["demo"])
    assert c == 0
def test_j():
    c,o,e = _R(["check",str(_S),"--open","--editor","custom:code --goto %f:%l","--dry-run"])
    assert "[dry-run open]" in e and "code --goto" in e

