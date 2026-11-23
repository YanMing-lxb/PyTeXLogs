"""日志文本编码辅助：多编码尝试与乱码留痕。"""

import logging
from pathlib import Path

logger = logging.getLogger(__name__)

#: 日志解码候选编码（按"误判概率从低到高"排序）。
#:
#: 说明：
#: - ``utf-8-sig`` 只在有 BOM 时才会与 ``utf-8`` 产生差异；它同样能解码所有
#:   合法 UTF-8 字节，因此不再单列 ``utf-8``，避免一次无意义的重复尝试；
#: - 不再保留 ``gbk``：``gb18030`` 是 GBK 的超集，任何合法 GBK 字节都能被
#:   ``gb18030`` 解出，单列 ``gbk`` 只会增加一次无意义的解码尝试；
#: - 不再保留 ``latin-1``：它对任意字节都能"成功"解码，会把 GBK/Shift-JIS
#:   等日志静默解成乱码，使错误文本无法定位。真正的不可解码日志会落到
#:   下面的 ``errors="replace"`` 兜底并打印警告。
FALLBACK_ENCODINGS: tuple[str, ...] = (
    "utf-8-sig",
    "gb18030",
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
