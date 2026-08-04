"""PyTeXLogs 自定义异常类。"""


class PyTeXLogsError(Exception):
    """PyTeXLogs 基础异常类。"""


class ParseError(PyTeXLogsError):
    """日志解析错误。"""


class ParserNotFoundError(PyTeXLogsError):
    """未找到匹配的解析器。"""


class ReportError(PyTeXLogsError):
    """报告读写错误。"""