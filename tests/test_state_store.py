"""用例：ProjectStateStore —— 单文件多命名空间状态存储。

核心保障：
  1. 命名空间隔离：写 pytexmk 不会抹掉 pytexlogs，反之亦然（历史上
     save_cache() 是整文件覆写，必然互相覆盖）。
  2. 严格 schema v3：旧扁平格式读取即丢弃。
  3. 原子写：中断不会留下半截 JSON。
  4. 任何异常都降级为空状态，绝不打断主流程。
"""

import json

import pytest

from pytexlogs import ProjectStateStore
from pytexlogs.core.state import (
    PROJECT_STATE_FILENAME,
    SCHEMA_VERSION,
    StateFileCorrupted,
)


def test_filename_constant():
    """文件名单点定义，两个库必须指向同一个文件。"""
    assert PROJECT_STATE_FILENAME == ".pytexmk_refcache.json"
    assert SCHEMA_VERSION == 3


def test_load_missing_returns_skeleton(tmp_path):
    store = ProjectStateStore(tmp_path, "main")
    assert store.load() == {"schema_version": SCHEMA_VERSION}


def test_update_refs_creates_namespace(tmp_path):
    store = ProjectStateStore(tmp_path, "main")
    assert store.update_refs(keys=["b", "a"], key_counts={"a": 1, "b": 2}) is True

    on_disk = json.loads((tmp_path / PROJECT_STATE_FILENAME).read_text(encoding="utf-8"))
    assert on_disk["schema_version"] == 3
    assert on_disk["pytexlogs"]["refs"]["keys"] == ["b", "a"]
    assert on_disk["pytexlogs"]["refs"]["key_counts"] == {"a": 1, "b": 2}


def test_namespaces_do_not_clobber_each_other(tmp_path):
    """核心回归：pytexlogs 与 pytexmk 各写各的，双方数据都还在。"""
    store = ProjectStateStore(tmp_path, "main")
    store.update_refs(keys=["cite1"])
    store.update_build(fingerprint="sha256:abc", round=3)

    data = store.load()
    assert data["pytexlogs"]["refs"]["keys"] == ["cite1"]
    assert data["pytexmk"]["build"]["fingerprint"] == "sha256:abc"
    assert data["pytexmk"]["build"]["round"] == 3


def test_update_build_merges_instead_of_replacing(tmp_path):
    store = ProjectStateStore(tmp_path, "main")
    store.update_build(fingerprint="f1", round=2, converged=True)
    store.update_build(round=3)

    build = store.get_build()
    assert build["fingerprint"] == "f1"  # 旧键保留
    assert build["round"] == 3  # 新键覆盖
    assert build["converged"] is True


def test_replace_namespace_drops_old_keys(tmp_path):
    store = ProjectStateStore(tmp_path, "main")
    store.update_build(a=1, b=2)
    store.replace_namespace("pytexmk", {"other": True})

    assert store.get_namespace("pytexmk") == {"other": True}


@pytest.mark.parametrize("payload", ["{not json", "[]", '"a string"', "null", ""])
def test_corrupted_file_degrades_to_empty(tmp_path, payload):
    """坏文件不能让编译崩掉，也不能被删（留给下次覆写修好）。"""
    path = tmp_path / PROJECT_STATE_FILENAME
    path.write_text(payload, encoding="utf-8")

    store = ProjectStateStore(tmp_path, "main")
    assert store.load() == {"schema_version": SCHEMA_VERSION}
    assert path.exists() or payload == ""


def test_v2_legacy_file_is_discarded(tmp_path):
    """严格 v3：旧扁平格式（v2）不再兼容，读到即丢弃。"""
    path = tmp_path / PROJECT_STATE_FILENAME
    path.write_text(
        json.dumps(
            {
                "schema_version": 2,
                "timestamp": "2026-10-17T14:54:10+00:00",
                "keys": ["legacy1", "legacy2"],
                "key_counts": {"legacy1": 1},
            }
        ),
        encoding="utf-8",
    )

    store = ProjectStateStore(tmp_path, "main")
    assert store.load() == {"schema_version": SCHEMA_VERSION}
    assert store.get_refs() == {}


def test_v2_file_gets_upgraded_on_next_write(tmp_path):
    path = tmp_path / PROJECT_STATE_FILENAME
    path.write_text(json.dumps({"schema_version": 2, "keys": ["x"]}), encoding="utf-8")

    store = ProjectStateStore(tmp_path, "main")
    store.update_refs(keys=["fresh"])

    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["schema_version"] == 3
    assert data["pytexlogs"]["refs"]["keys"] == ["fresh"]


def test_atomic_write_leaves_no_temp_files(tmp_path):
    store = ProjectStateStore(tmp_path, "main")
    for i in range(5):
        store.update_build(round=i)

    leftovers = [p.name for p in tmp_path.iterdir() if p.suffix == ".tmp"]
    assert leftovers == []


def test_lock_file_is_released(tmp_path):
    store = ProjectStateStore(tmp_path, "main")
    store.update_build(round=1)

    assert not store.lock_path.exists()


def test_concurrent_style_updates_accumulate(tmp_path):
    """模拟两个工具交替写入，双方的键都不能丢。"""
    logs = ProjectStateStore(tmp_path, "main")
    mk = ProjectStateStore(tmp_path, "main")

    for i in range(3):
        logs.update_refs(keys=[f"k{i}"])
        mk.update_build(round=i)

    data = ProjectStateStore(tmp_path, "main").load()
    assert data["pytexlogs"]["refs"]["keys"] == ["k2"]
    assert data["pytexmk"]["build"]["round"] == 2


def test_clear_removes_file(tmp_path):
    store = ProjectStateStore(tmp_path, "main")
    store.update_build(round=1)
    assert store.path.exists()

    assert store.clear() is True
    assert not store.path.exists()
    assert store.clear() is True  # 幂等


def test_creates_missing_auxdir(tmp_path):
    target = tmp_path / "Auxiliary" / "nested"
    store = ProjectStateStore(target, "main")

    assert store.update_build(round=1) is True
    assert store.path.exists()


def test_timestamp_and_job_recorded(tmp_path):
    store = ProjectStateStore(tmp_path, "main")
    store.update_build(round=1)

    data = store.load()
    assert "timestamp" in data
    assert "main" in data["jobs"]


def test_state_file_corrupted_exception_is_exportable():
    """异常类型对外可见，供调用方做精细化处理。"""
    assert issubclass(StateFileCorrupted, Exception)
