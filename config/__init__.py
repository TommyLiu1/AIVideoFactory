import os
import sys
from datetime import datetime
from loguru import logger
from config import config


def __init_logger():
    _lvl = config.log_level
    root_dir = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))

    # 创建日志目录（如果不存在）
    log_dir = os.path.join(root_dir, "logs")
    os.makedirs(log_dir, exist_ok=True)

    # 日志文件名（按日期）
    log_file = os.path.join(log_dir, f"server_{datetime.now().strftime('%Y%m%d')}.log")
    def format_record(record):
        # 获取日志记录中的文件全路径
        file_path = record["file"].path
        # 将绝对路径转换为相对于项目根目录的路径
        relative_path = os.path.relpath(file_path, root_dir)
        # 更新记录中的文件路径
        record["file"].path = f"./{relative_path}"
        # 返回修改后的格式字符串
        # 您可以根据需要调整这里的格式
        _format = (
            "<green>{time:%Y-%m-%d %H:%M:%S}</> | "
            + "<level>{level}</> | "
            + '"{file.path}:{line}":<blue> {function}</> '
            + "- <level>{message}</>"
            + "\n"
        )
        return _format

    logger.remove()

    # logger.add(
    #     sys.stdout,
    #     level=_lvl,
    #     format=format_record,
    #     colorize=True,
    # )
    # 添加文件输出
    logger.add(
        log_file,
        level=_lvl,
        format=format_record,
        rotation="00:00",  # 每天午夜创建新文件
        retention="10 days",  # 保留30天的日志
        compression="zip",  # 旧日志压缩为zip
        encoding="utf-8",
        enqueue=True,  # 异步写入
    )

__init_logger()
