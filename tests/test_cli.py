"""Task 6: CLI 端到端测试（覆盖 check/summary/export/demo 4 子命令 + TR-6.1~6.5）。"""
import json
import subprocess
import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_FIXTURES_DIR = _PROJECT_ROOT / "tests" / "fixtures"
_SAMPLE_LOG = _FIXTURES_DIR / "sample.log"


def _run_cli(*args: str, cwd: Path | None = None) -> subprocess.CompletedProcess:
    """以模块方式运行 pytexlogs.cli，返回 CompletedProcess（cwd 默认项目根）。"""
    cmd = [sys.executable, "-m", "pytexlogs.cli", *args]
    return subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        cwd=str(cwd or _PROJECT_ROOT),
        check=False,
    )


class TestVersionHelp:
    """B1 + B2: --version / --help 基础行为。"""

    def test_version(self):
        """B1/TR-6.1: --version stdout 含 pytexlogs 0.3.0，exitcode=0。"""
        r = _run_cli("--version")
        assert r.returncode == 0, f"stderr={r.stderr}"
        assert "pytexlogs" in r.stdout
        assert "0.3.0" in r.stdout

    def test_help_lists_subcmds(self):
        """B2/TR-6.2: --help 列出 check/summary/export/demo 四字命令字样。"""
        r = _run_cli("--help")
        assert r.returncode == 0, f"stderr={r.stderr}"
        for name in ("check", "summary", "export", "demo"):
            assert name in r.stdout, f"help 输出缺少子命令 {name!r}"


class TestCheckSubcommand:
    """B3: check 子命令 exitcode 行为。"""

    def test_check_exit_1_on_error_sample(self):
        """B3/TR-6.3: sample.log 含 ERROR，check 返回 1，stdout 含 ERROR 或错误文本。"""
        r = _run_cli("check", str(_SAMPLE_LOG))
        assert r.returncode == 1, f"stdout={r.stdout}\nstderr={r.stderr}"
        haystack = (r.stdout or "") + " " + (r.stderr or "")
        assert ("Undefined control sequence" in haystack) or ("ERROR" in haystack), haystack[:500]


class TestSummarySubcommand:
    """B4: summary 子命令不因 ERROR 修改退出码。"""

    def test_summary_exit_0(self):
        """B4: summary 即使日志含 error，也返回 exitcode=0。"""
        r = _run_cli("summary", str(_SAMPLE_LOG))
        assert r.returncode == 0, f"summary 不应因 error 修改 exitcode。stdout={r.stdout}\nstderr={r.stderr}"


class TestExportSubcommand:
    """B5: export SARIF 行为。"""

    def test_export_sarif(self, tmp_path: Path):
        """B5/TR-6.5: export --format sarif 写到 out.sarif，json.load 通过且含关键键。"""
        out_file = tmp_path / "out.sarif"
        r = _run_cli(
            "export",
            "--format", "sarif",
            str(_FIXTURES_DIR),
            "--output", str(out_file),
        )
        if not out_file.exists():
            # fallback: 直接用 sample.log 位置参数
            r2 = _run_cli(
                "export",
                "--format", "sarif",
                str(_SAMPLE_LOG),
                "--output", str(out_file),
            )
            r = r2
        assert out_file.exists(), f"out.sarif 未生成。stdout={r.stdout}\nstderr={r.stderr}"
        data = json.loads(out_file.read_text(encoding="utf-8"))
        assert "$schema" in data
        runs = data.get("runs") or []
        assert len(runs) >= 1, "SARIF runs 列表为空"
        driver = runs[0].get("tool", {}).get("driver", {})
        assert driver.get("name") == "pytexlogs", f"driver.name={driver.get('name')!r}"


class TestDemoSubcommand:
    """B6: demo 子命令。"""

    def test_demo_ok(self):
        """B6: demo 子命令 exitcode=0。"""
        r = _run_cli("demo")
        assert r.returncode == 0, f"demo 失败：stdout={r.stdout}\nstderr={r.stderr}"


class TestEditorOpen:
    """B7/TR-6.5: --open --dry-run 编辑器模板替换。"""

    def test_open_dry_run_custom_editor(self):
        """B7/TR-6.5: custom 模板 + dry-run → stderr 含 [dry-run open] + code --goto 替换后的命令。"""
        r = _run_cli(
            "check",
            str(_SAMPLE_LOG),
            "--open",
            "--editor", "custom:code --goto %f:%l",
            "--dry-run",
        )
        assert "[dry-run open]" in r.stderr, f"未打印 dry-run 标记：stderr={r.stderr!r}"
        assert "code --goto" in r.stderr, f"模板未生效：stderr={r.stderr!r}"
        # 应有文件:行号 的替换结果
        assert ":" in r.stderr and any(c.isdigit() for c in r.stderr), r.stderr


class TestNoRichGuarantee:
    """B8/TR-6.4: CLI 不强依赖 rich。"""

    def test_no_rich_import_for_simple_run(self, tmp_path: Path):
        """B8/TR-6.4: 用独立解释器进程验证不 import rich 也能跑通 check 子命令。

        通过 subprocess 跑一段脚本：在 sys.modules 中预先屏蔽 rich 相关模块，再执行 main()。
        """
        script = tmp_path / "no_rich_probe.py"
        script.write_text(
            r"""
import sys
# 屏蔽 rich 相关 import
class _Blocker:
    def find_module(self, name, path=None):
        if name == "rich" or name.startswith("rich."):
            return self
        return None
    def load_module(self, name):
        raise ImportError(f"rich blocked for test: {name}")
sys.meta_path.insert(0, _Blocker())
# 保险起见清掉已导入
for k in list(sys.modules):
    if k == "rich" or k.startswith("rich."):
        del sys.modules[k]

from pytexlogs.cli import main
rc = main(["check", r""" + '"' + str(_SAMPLE_LOG).replace("\\", "\\\\") + '"' + r"""])
# exitcode 应该是 1（sample.log 有 error）
print("RC=", rc)
sys.exit(0 if rc in (0, 1) else 2)
""",
            encoding="utf-8",
        )
        r = subprocess.run(
            [sys.executable, str(script)],
            capture_output=True,
            text=True,
            cwd=str(_PROJECT_ROOT),
            check=False,
        )
        assert r.returncode == 0, f"屏蔽 rich 后 CLI 异常。stdout={r.stdout}\nstderr={r.stderr}"
        assert "RC=" in r.stdout, f"未到达 main 返回。stdout={r.stdout}\nstderr={r.stderr}"
