"""日志文本编码辅助：多编码尝试与乱码留痕。"""

import logging
from pathlib import Path

logger = logging.getLogger(__name__)

#: 日志解码候选编码（按"误判概率从低到高"排序）。
#:
#: 说明：
#: - ``utf-8-sig`` 只在有 BOM 时才会与 ``utf-8`` 产生差异；它同样能解码所有
#:   合法 UTF-8 字节，因此不再单列 ``utf-8``，避免一次无意义的重复尝试；
#: - 不再保留 ``utf-8``：``utf-8-sig`` 覆盖它；
#: - ``latin-1`` 只能放在**最后**：它对任意字节都能成功解码，放在前面会把
#:   GBK/Shift-JIS 日志静默解成乱码。只有 UTF-8/GB18030 都失败时才说明日志
#:   是 TeX 直接吐出的 8-bit 字节（例如 ``Erişen`` 被写成 ``Eri\xb3en``），
#:   此时 latin-1 能保留原文而不是替换成 U+FFFD。
FALLBACK_ENCODINGS: tuple[str, ...] = (
    "utf-8-sig",
    "gb18030",
    "latin-1",
)


def read_log_text(log_path: str | Path) -> str:
    """读取日志文件，多编码兜底。

    依次尝试 :data:`FALLBACK_ENCODINGS`；全部失败时用 ``utf-8`` +
    ``errors="replace"`` 兜底，并记录一条 warning（乱码日志要在日志里留痕，
    否则解析出来的错误文本会"看起来正常但内容错位"）。
    """
    path = Path(log_path)
    data = path.read_bytes()
    for encoding in FALLBACK_ENCODINGS:
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue

    logger.warning(
        "日志 %s 无法用 %s 解码，已按 utf-8 + replace 兜底，错误文本可能出现乱码",
        path,
        "/".join(FALLBACK_ENCODINGS),
    )
    return data.decode("utf-8", errors="replace")
