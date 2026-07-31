import shutil
import subprocess
import sys
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

try:  # rich 是 PyTeXLogs dev 依赖（运行 make 目标时已 uv sync --dev 安装）
    from rich.console import Console
    from rich.table import Table
    from rich.theme import Theme

    _RICH_AVAILABLE = True
except Exception:  # noqa: BLE001 - 无 rich 时 fallback 到标准库 print
    _RICH_AVAILABLE = False
    Console = None  # type: ignore[assignment,misc]
    Table = None  # type: ignore[assignment,misc]
    Theme = None  # type: ignore[assignment,misc]

if hasattr(sys.stdout, "reconfigure"):
    try:
        if sys.stdout.encoding != "UTF-8":
            sys.stdout.reconfigure(encoding="utf-8")
    except Exception:  # noqa: BLE001
        pass

# -----------------------------------------------------------------------
# <<<<<<<<<<<<<<<<<<<<<<<<<<<<| 主题与样式配置 |>>>>>>>>>>>>>>>>>>>>>>>>>>>>
# -----------------------------------------------------------------------
if _RICH_AVAILABLE:
    custom_theme = Theme({
        "success": "bold green",
        "warning": "bold yellow",
        "error": "bold red",
        "info": "bold blue",
        "status": "bold cyan",
        "time": "bold magenta",
    })
    console = Console(theme=custom_theme)
else:
    class _FallbackConsole:
        """Fallback console：当用户环境没装 rich 时也能正常输出 make 目标结果。"""

        def print(self, *objects: Any, **kwargs: Any) -> None:  # noqa: ANN001,D401
            # 去掉 rich markup 标签 [xxx]、[/xxx] 后再 print
            import re as _re
            def _strip(txt: object) -> str:
                pat = _re.compile(r"\[/?[^\]]+\]")
                return pat.sub("", str(txt))
            sep = kwargs.pop("sep", " ")
            end = kwargs.pop("end", "\n")
            style = kwargs.pop("style", None)  # noqa: F841 - 未使用，保持签名兼容
            _ = kwargs
            cleaned = [_strip(o) for o in objects]
            print(*cleaned, sep=sep, end=end)

        def status(self, *args: Any, **kwargs: Any):  # noqa: ANN001,D401
            # 忽略动态 status，直接返回一个空上下文
            import contextlib
            return contextlib.nullcontext()

        def log(self, *objects: Any, **kwargs: Any) -> None:  # noqa: ANN001,D401
            self.print(*objects, **kwargs)

    console = _FallbackConsole()


# -----------------------------------------------------------------------
# <<<<<<<<<<<<<<<<<<<<<<<<<<<<<| 性能统计模块 |>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
# -----------------------------------------------------------------------
class PerformanceTracker:
    """跟踪多步骤执行时间，生成可视化性能报告。"""

    def __init__(self) -> None:
        self.records: list[dict[str, Any]] = []

    def add_record(self, performance_data: dict[str, Any]) -> None:  # noqa: D401
        self.records.append({
            "name": performance_data.get("name"),
            "duration": performance_data.get("duration"),
            "status": performance_data.get("status"),
        })

    def execute_with_timing(self, func: Callable[..., Any], step_name: str) -> tuple:  # noqa: D401
        start_time = time.time()
        try:
            result = func()
            duration = time.time() - start_time
            status = "成功" if result else "失败"
            return result, {"name": step_name, "duration": duration, "status": status}
        except Exception as e:  # noqa: BLE001
            duration = time.time() - start_time
            console.print(f"❌ [{step_name}] 执行异常 - 耗时: {duration:.2f}s, 错误: {e!s}")
            return False, {"name": step_name, "duration": duration, "status": "异常"}

    def generate_report(self) -> None:  # noqa: D401
        if _RICH_AVAILABLE:
            table = Table(title="性能报告")
            table.add_column("步骤", justify="left", style="cyan")
            table.add_column("耗时(秒)", justify="right", style="magenta")
            table.add_column("状态", justify="center")
            total_time = sum(r["duration"] for r in self.records)
            for r in self.records:
                status_color = "green" if r["status"] == "成功" else "red" if r["status"] == "失败" else "yellow"
                table.add_row(r["name"], f"{r['duration']:.2f}s", f"[{status_color}]{r['status']}[/]")
            table.add_row("总耗时", f"{total_time:.2f}s", "")
            console.print(table)
        else:
            total_time = 0.0
            console.print("=== 性能报告 ===")
            for r in self.records:
                console.print(f"- {r['name']}: {r['duration']:.2f}s  {r['status']}")
                total_time += r["duration"]
            console.print(f"- 总耗时: {total_time:.2f}s")
            console.print("================")


# ======================
# 工具函数
# ======================


def run_command(  # noqa: D401,PLR0913
    command: list,
    success_msg: str,
    error_msg: str,
    process_name: str = "执行命令",
    encoding: str = "utf-8",
    cwd: str | Path | None = None,
) -> bool:
    try:
        console.print(f"[dim]执行命令: {' '.join(str(c) for c in command)}[/]")
        start_time = time.time()
        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            encoding=encoding,
            errors="ignore",
            cwd=str(cwd) if cwd else None,
        )

        with console.status(f"[status]正在{process_name}..."):
            while True:
                output = process.stdout.readline() if process.stdout else ""
                if not output and process.poll() is not None:
                    break
                if output:
                    console.print(f"[dim]{output.strip()}[/]")

        if process.returncode == 0:
            duration = time.time() - start_time
            format_duration = (
                f"{duration // 60:.0f}m {duration % 60:.1f}s" if duration > 60 else f"{duration:.2f}s"
            )
            console.print(f"✓ {success_msg} [time](耗时: {format_duration})[/]", style="success")
            return True

        raise subprocess.CalledProcessError(process.returncode, command, f"退出码: {process.returncode}")
    except subprocess.CalledProcessError as e:
        console.print(f"✗ {error_msg}: {e}", style="error")
        return False


def delete_folder(folder_path: str | Path) -> bool:  # noqa: D401
    """删除指定文件夹及所有内容（不存在也算成功）。"""
    path = Path(folder_path)
    if not path.exists():
        console.print(f"⚠️ 文件夹不存在：{path}", style="warning")
        return True
    try:
        shutil.rmtree(path)
        console.print(f"✓ 已删除文件夹：{path}", style="success")
        return True
    except Exception as e:  # noqa: BLE001
        console.print(f"✗ 删除失败：{e}", style="error")
        return False


def delete_file_glob(pattern: str) -> bool:  # noqa: D401
    """递归删除匹配 pattern 的文件（例如 **.pyc、**/.pyd）。"""
    import glob
    ok = True
    for f in glob.glob(pattern, recursive=True):
        p = Path(f)
        try:
            if p.is_file():
                p.unlink()
                console.print(f"✓ 已删除文件：{p}", style="success")
        except Exception as e:  # noqa: BLE001
            console.print(f"✗ 删除 {p} 失败：{e}", style="error")
            ok = False
    return ok


if __name__ == "__main__":
    # 兼容调用：python utils.py clean 用于临时测试
    if len(sys.argv) > 1 and sys.argv[1] == "clean":
        delete_folder("dist")
