"""单文件多命名空间状态存储：多个工具共享一个状态文件时的唯一写入者。

设计要点（DO NOT BREAK）
------------------------
1. **一个项目一个文件**：``<auxdir>/.pytexmk_refcache.json``。PyTeXMK / PyTeXLogs
   以及未来的第三方工具都写这一个文件，绝不新增第二个状态文件。
2. **命名空间隔离**：每个写入者只拥有自己的顶层键（``pytexlogs`` / ``pytexmk``
   / ...）。读-改-写（read-modify-write）保证不会覆盖别人的键。
3. **schema v3 严格模式**：旧版扁平格式（v2，顶层直接放 ``keys`` /
   ``key_counts``）不再兼容，读到即丢弃。这样文件结构只有一种形态，无需
   维护双写逻辑。
4. **原子替换**：先写同目录临时文件再 ``os.replace``，保证 Ctrl+C 中断时不会
   留下半截 JSON——状态文件一旦损坏，整个"跨进程续编"能力就退化成重新编译。
5. **绝不因状态文件异常而中断主流程**：任何 IO / 解析错误都降级为"空骨架"，
   并把异常原因交给调用方决定是否提示。
"""

import json
import logging
import os
import tempfile
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

__all__ = [
    "PROJECT_STATE_FILENAME",
    "SCHEMA_VERSION",
    "ProjectStateStore",
    "StateFileCorrupted",
]

logger = logging.getLogger(__name__)

#: 项目级状态文件名（所有工具共用这一个文件）
PROJECT_STATE_FILENAME = ".pytexmk_refcache.json"

#: 当前状态文件 schema 版本
SCHEMA_VERSION = 3

#: 锁文件后缀；与状态文件同目录
_LOCK_SUFFIX = ".lock"

#: 获取锁的最长等待时间（秒）；超时则放弃写入，让主流程继续
_DEFAULT_LOCK_TIMEOUT = 2.0


class StateFileCorrupted(Exception):
    """状态文件内容损坏或版本不受支持时抛出（仅供调用方感知，不向外冒泡）。"""


def _empty_state() -> dict[str, Any]:
    """返回一个符合当前 schema 的空状态骨架。"""
    return {"schema_version": SCHEMA_VERSION}


class ProjectStateStore:
    """项目状态文件的读写门面：命名空间隔离 + 原子写 + 可选文件锁。

    典型用法::

        store = ProjectStateStore(auxdir, jobname="main")
        build = store.get_namespace("pytexmk").get("build", {})
        store.update_namespace("pytexmk", build={"fingerprint": "..."})

    ``jobname`` 目前只用于日志与将来的多主文件场景；状态文件本身按
    ``auxdir`` 定位，同一 auxdir 下的多个 jobname 共享一份文件、各自占一个键。
    """

    def __init__(
        self,
        auxdir: str | Path,
        jobname: str | None = None,
        *,
        filename: str = PROJECT_STATE_FILENAME,
        lock_timeout: float = _DEFAULT_LOCK_TIMEOUT,
    ) -> None:
        """初始化：定位状态文件路径，记录锁超时时间。"""
        self.auxdir = Path(auxdir)
        self.jobname = jobname or "default"
        self.path = self.auxdir / filename
        self.lock_path = self.auxdir / f"{filename}{_LOCK_SUFFIX}"
        self.lock_timeout = lock_timeout

    # ---------------------------------------------------------------- 读取

    def load(self) -> dict[str, Any]:
        """读取完整状态字典；文件缺失/损坏/版本不符时返回空骨架。

        严格 v3：遇到 ``schema_version`` 不为 3 的文件直接丢弃内容（仅记日志），
        这样无需维护旧格式迁移分支。
        """
        if not self.path.exists():
            return _empty_state()
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError, UnicodeDecodeError) as exc:
            logger.debug("状态文件无法解析，按空状态处理: %s (%s)", self.path, exc)
            return _empty_state()
        if not isinstance(raw, dict):
            logger.debug("状态文件顶层不是对象，按空状态处理: %s", self.path)
            return _empty_state()
        version = raw.get("schema_version")
        if version != SCHEMA_VERSION:
            logger.warning(
                "状态文件 schema 版本不受支持（%s，需要 %s），已忽略其内容: %s",
                version,
                SCHEMA_VERSION,
                self.path,
            )
            return _empty_state()
        return raw

    def get_namespace(self, name: str) -> dict[str, Any]:
        """读取某个工具命名空间；不存在或类型异常时返回空字典。"""
        namespace = self.load().get(name)
        if isinstance(namespace, dict):
            return namespace
        return {}

    def get_build(self) -> dict[str, Any]:
        """读取 PyTeXMK 的构建状态段（``pytexmk.build``）。"""
        build = self.get_namespace("pytexmk").get("build")
        if isinstance(build, dict):
            return build
        return {}

    def get_refs(self) -> dict[str, Any]:
        """读取 PyTeXLogs 的引用缓存段（``pytexlogs.refs``）。"""
        refs = self.get_namespace("pytexlogs").get("refs")
        if isinstance(refs, dict):
            return refs
        return {}

    # ---------------------------------------------------------------- 写入

    def update_namespace(self, name: str, **kwargs: Any) -> bool:
        """对某个命名空间做浅合并写入；返回是否真正写盘。

        只替换 ``kwargs`` 中出现的键，命名空间内其它键原样保留。
        """
        return self._mutate(lambda state: self._merge_namespace(state, name, kwargs))

    def update_build(self, **kwargs: Any) -> bool:
        """更新 ``pytexmk.build`` 下的若干键。"""
        return self.update_namespace("pytexmk", build={**self.get_build(), **kwargs})

    def update_refs(self, **kwargs: Any) -> bool:
        """更新 ``pytexlogs.refs`` 下的若干键。"""
        return self.update_namespace("pytexlogs", refs={**self.get_refs(), **kwargs})

    def replace_namespace(self, name: str, value: dict[str, Any]) -> bool:
        """整体替换某个命名空间（该命名空间自己的数据，不涉及别人）。"""
        return self._mutate(lambda state: self._set_namespace(state, name, value))

    def clear(self) -> bool:
        """删除状态文件（``pytexmk -c`` 等清理场景使用）。"""
        try:
            self.path.unlink(missing_ok=True)
        except OSError as exc:
            logger.debug("删除状态文件失败: %s (%s)", self.path, exc)
            return False
        return True

    # ------------------------------------------------------------ 内部实现

    @staticmethod
    def _merge_namespace(state: dict[str, Any], name: str, updates: dict[str, Any]) -> None:
        """把 updates 浅合并进 state[name]。"""
        target = state.get(name)
        if not isinstance(target, dict):
            target = {}
        target.update(updates)
        state[name] = target

    @staticmethod
    def _set_namespace(state: dict[str, Any], name: str, value: dict[str, Any]) -> None:
        """整体设置 state[name]。"""
        state[name] = value

    def _mutate(self, mutator) -> bool:
        """在锁内读-改-写，原子落盘；任何异常都不外抛。"""
        try:
            self.auxdir.mkdir(parents=True, exist_ok=True)
            with self._locked():
                state = self.load()
                mutator(state)
                state["schema_version"] = SCHEMA_VERSION
                if self.jobname:
                    state.setdefault("jobs", {})
                    jobs = state["jobs"]
                    if isinstance(jobs, dict):
                        jobs[self.jobname] = {"updated_at": _now_iso()}
                state["timestamp"] = _now_iso()
                self._atomic_write(state)
            return True
        except OSError as exc:
            logger.debug("写入状态文件失败（不影响主流程）: %s (%s)", self.path, exc)
            return False

    def _atomic_write(self, state: dict[str, Any]) -> None:
        """写同目录临时文件后 os.replace，保证读者永远看到完整文件。"""
        payload = json.dumps(state, ensure_ascii=False, indent=2, sort_keys=False)
        fd, tmp_name = tempfile.mkstemp(
            dir=str(self.auxdir), prefix=f".{self.path.name}.", suffix=".tmp"
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
                handle.write(payload)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(tmp_name, self.path)
        except BaseException:
            try:
                os.unlink(tmp_name)
            except OSError:
                pass
            raise

    @contextmanager
    def _locked(self) -> Iterator[None]:
        """尽力而为的文件锁：占用则短暂轮询，超时则放弃写入（降级而非报错）。

        状态文件丢一次更新只会让下一次编译多跑一轮，属于可接受降级；因此这里
        不做阻塞等待，也不抛异常。
        """
        acquired = False
        try:
            acquired = self._try_acquire()
            if not acquired:
                logger.debug("状态文件被其它进程占用，跳过本次写入: %s", self.lock_path)
            yield
        finally:
            if acquired:
                try:
                    self.lock_path.unlink(missing_ok=True)
                except OSError:
                    pass

    def _try_acquire(self) -> bool:
        """尝试创建锁文件；超时返回 False。"""
        deadline = _monotonic() + max(0.0, self.lock_timeout)
        while True:
            try:
                fd = os.open(str(self.lock_path), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            except FileExistsError:
                self._break_stale_lock()
                if _monotonic() >= deadline:
                    return False
                _sleep(0.02)
                continue
            except OSError:
                return False
            os.close(fd)
            return True

    def _break_stale_lock(self) -> None:
        """清理明显过期的锁（进程被 kill 时留下的），避免永久锁死。"""
        try:
            mtime = self.lock_path.stat().st_mtime
        except OSError:
            return
        if _time_now() - mtime > 30.0:
            try:
                self.lock_path.unlink(missing_ok=True)
            except OSError:
                pass


def _now_iso() -> str:
    """当前本地时区的 ISO 时间字符串（带偏移）。"""
    return datetime.now(tz=UTC).astimezone().isoformat()


def _monotonic() -> float:
    """单调时钟秒数。"""
    import time

    return time.monotonic()


def _time_now() -> float:
    """挂钟秒数。"""
    import time

    return time.time()


def _sleep(seconds: float) -> None:
    """短暂休眠。"""
    import time

    time.sleep(seconds)
