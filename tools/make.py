"""
 =======================================================================
Author       : 焱铭
Date         : 2025-07-16 20:53:22 +0800
LastEditTime : 2026-07-31 (PyTeXLogs 独立库适配)
Github       : https://github.com/YanMing-lxb/
Description  : PyTeXLogs Make 目标调用脚本（与 PyTeXMK Makefile UX 对齐）
 =======================================================================
"""

import re
import subprocess
import sys
from pathlib import Path

# 允许 `python tools/make.py <target>` 直接运行时正确找到同目录下的 utils/config
sys.path.insert(0, str(Path(__file__).parent))

from config import PROJECT_NAME, ROOT_DIR, SRC_DIR  # type: ignore[import-not-found]
from utils import PerformanceTracker, console, delete_file_glob, delete_folder, run_command  # type: ignore[import-not-found]


def _get_version() -> str:
    version_file = SRC_DIR / "version.py"
    if not version_file.exists():
        raise FileNotFoundError(f"文件 {version_file} 不存在")
    content = version_file.read_text(encoding="utf-8")
    match = re.search(r"__version__\s*=\s*['\"]([^'\"]+)['\"]", content)
    if not match:
        raise ValueError(f"无法在 {version_file} 中找到 __version__ 变量")
    return match.group(1)


def clean() -> bool:
    """清理所有构建和测试产生的临时目录与文件。"""
    console.print("🧹 开始清理 PyTeXLogs 构建产物", style="status")
    tracker = PerformanceTracker()

    def _step_clean_build_dirs() -> bool:
        ok = True
        for folder_name in ("dist", "build", "srcpyd", ".pytest_cache", "ruff_cache", ".coverage"):
            ok &= delete_folder(ROOT_DIR / folder_name)
        import glob as _g
        for pycache in _g.glob(str(ROOT_DIR / "**" / "__pycache__"), recursive=True):
            delete_folder(pycache)
        return ok

    def _step_clean_bytecode() -> bool:
        ok = True
        for pattern in ("**/*.pyc", "**/*.pyo", "**/*.pyd"):
            ok &= delete_file_glob(str(ROOT_DIR / pattern))
        return ok

    _, info1 = tracker.execute_with_timing(_step_clean_build_dirs, "清理构建/缓存目录")
    _, info2 = tracker.execute_with_timing(_step_clean_bytecode, "清理 Python 字节码")
    tracker.add_record(info1)
    tracker.add_record(info2)
    tracker.generate_report()
    console.print("🎉 清理完成！", style="success")
    return info1["status"] == "成功" and info2["status"] == "成功"


def whl() -> bool:
    """先 clean，再构建 wheel + sdist 分发包。"""
    console.print(f"📦 开始构建 PyTeXLogs 分发包（v{_get_version()}）", style="status")
    tracker = PerformanceTracker()

    _, info1 = tracker.execute_with_timing(clean, "清理旧构建产物")
    tracker.add_record(info1)

    def _build() -> bool:
        return run_command(
            command=["uv", "build"],
            success_msg="PyTeXLogs wheel + sdist 构建成功",
            error_msg="PyTeXLogs 分发包构建失败",
            process_name="执行 uv build 构建分发包",
            cwd=ROOT_DIR,
        )

    _, info2 = tracker.execute_with_timing(_build, "构建分发包 (wheel + sdist)")
    tracker.add_record(info2)
    tracker.generate_report()
    if info2["status"] == "成功":
        dist = ROOT_DIR / "dist"
        if dist.exists():
            console.print("📋 构建产物一览：", style="info")
            for f in sorted(dist.iterdir()):
                if f.is_file():
                    size_kb = f.stat().st_size / 1024
                    console.print(f"  - {f.name}  [dim]({size_kb:.2f} KB)[/]", style="info")
        console.print("🎉 构建完成！", style="success")
    return info2["status"] == "成功"


def inswhl() -> bool:
    """构建 whl 后通过 uv run pip --force-reinstall 安装到当前开发环境。"""
    console.print("🧪 开始本地安装测试（pip install --force-reinstall）", style="status")
    tracker = PerformanceTracker()

    _, info1 = tracker.execute_with_timing(whl, "构建最新 wheel + sdist")
    tracker.add_record(info1)

    def _install() -> bool:
        dist = ROOT_DIR / "dist"
        whl_files = sorted(dist.glob(f"{PROJECT_NAME}-*.whl"))
        if not whl_files:
            raise FileNotFoundError(f"dist 目录中没有找到 {PROJECT_NAME} 的 .whl 文件")
        whl_path = whl_files[-1]
        return run_command(
            command=["uv", "run", "pip", "install", "--force-reinstall", str(whl_path)],
            success_msg=f"{PROJECT_NAME} 本地 wheel 安装完成",
            error_msg=f"{PROJECT_NAME} 本地 wheel 安装失败",
            process_name=f"pip --force-reinstall {whl_path.name}",
            cwd=ROOT_DIR,
        )

    _, info2 = tracker.execute_with_timing(_install, "本地 --force-reinstall 安装 wheel")
    tracker.add_record(info2)
    tracker.generate_report()
    if info2["status"] == "成功":
        console.print("🎉 本地安装完成！", style="success")
    return info2["status"] == "成功"


def upload() -> bool:
    """打本地 git tag 并推送（真正发布 PyPI 交给 CI Release.yml 的 trusted publishing）。"""
    version = _get_version()
    tag_name = f"v{version}"
    console.print(f"🏷️  准备创建并推送标签 {tag_name}", style="status")
    tracker = PerformanceTracker()

    def _create_tag() -> bool:
        return run_command(
            command=["git", "tag", tag_name],
            success_msg=f"本地标签 {tag_name} 创建成功",
            error_msg=f"本地标签 {tag_name} 创建失败（可能已存在）",
            process_name=f"创建 git tag {tag_name}",
            cwd=ROOT_DIR,
        )

    def _push_tag() -> bool:
        return run_command(
            command=["git", "push", "origin", tag_name],
            success_msg=f"标签 {tag_name} 推送到 origin 成功",
            error_msg=f"标签 {tag_name} 推送失败",
            process_name=f"推送 git tag {tag_name}",
            cwd=ROOT_DIR,
        )

    _, info1 = tracker.execute_with_timing(_create_tag, "创建本地标签")
    tracker.add_record(info1)
    _, info2 = tracker.execute_with_timing(_push_tag, "推送标签到 origin")
    tracker.add_record(info2)
    tracker.generate_report()
    if info2["status"] == "成功":
        console.print(
            f"✅ 标签 {tag_name} 已推送到 GitHub，CI Release.yml 会在 tag 事件触发时执行 PyPI 可信发布。",
            style="success",
        )
    return info2["status"] == "成功"


TARGETS = {
    "clean": clean,
    "whl": whl,
    "inswhl": inswhl,
    "upload": upload,
}


def main() -> None:
    if len(sys.argv) < 2 or sys.argv[1] not in TARGETS:
        console.print(f"用法: {sys.argv[0]} <目标>")
        console.print("可用目标:", ", ".join(TARGETS.keys()))
        sys.exit(1)

    target = sys.argv[1]
    try:
        ok = TARGETS[target]()
    except subprocess.CalledProcessError as e:
        console.print(f"执行命令时出错: {e}", style="error")
        sys.exit(1)
    except Exception as e:  # noqa: BLE001
        console.print(f"[{target}] 异常: {e}", style="error")
        sys.exit(1)

    sys.exit(0 if ok else 2)


if __name__ == "__main__":
    main()
