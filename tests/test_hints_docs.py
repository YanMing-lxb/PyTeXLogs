"""round6 P2-5：``docs/hints-reference.md`` 规则表与 ``RULE_IDS`` 顺序锁定。

文档表的 ``rule_id`` 必须与 :data:`pytexlogs.hints.RULE_IDS` 一一对应且顺序一致：
缺项、多项、顺序错位都必须失败。本测试只做一致性断言，不反向修改文档。
"""

import re
from pathlib import Path

from pytexlogs.hints import RULE_IDS

_DOC_PATH = Path(__file__).resolve().parent.parent / "docs" / "hints-reference.md"
_ROW_RE = re.compile(r"^\| `([a-z0-9_]+)` \|", re.MULTILINE)


def _doc_rule_ids() -> list[str]:
    text = _DOC_PATH.read_text(encoding="utf-8")
    return _ROW_RE.findall(text)


def test_doc_rule_ids_match_code_exactly() -> None:
    """文档规则表与 RULE_IDS 数量、成员、顺序完全一致。"""
    doc_ids = _doc_rule_ids()
    code_ids = list(RULE_IDS)

    assert len(doc_ids) == len(code_ids), (
        f"规则数量不一致：文档 {len(doc_ids)} 条，代码 {len(code_ids)} 条；"
        f"文档缺项={[r for r in code_ids if r not in doc_ids]}，"
        f"文档多项={[r for r in doc_ids if r not in code_ids]}"
    )
    assert doc_ids == code_ids, (
        "文档规则顺序与 RULE_IDS 不一致；"
        f"首个错位位置：{next((i for i, (a, b) in enumerate(zip(code_ids, doc_ids, strict=True)) if a != b), None)}"
    )


def test_doc_rule_ids_are_unique() -> None:
    """文档表内 rule_id 不允许重复。"""
    doc_ids = _doc_rule_ids()
    duplicates = [rule for rule in set(doc_ids) if doc_ids.count(rule) > 1]
    assert not duplicates, f"文档规则表存在重复 rule_id：{duplicates}"
