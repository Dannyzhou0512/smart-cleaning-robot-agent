import logging
from Agent_project.utils.path_tool import get_abs_path
import os
from datetime import datetime

#日志保存的根目录
LOG_ROOT = get_abs_path("logs")

#确保日志目录的存在
os.makedirs(LOG_ROOT, exist_ok=True)

#日志的格式的配置 error info debug
DEFAULT_LOG_FORMAT = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def get_logger(
        name:str = "agent",
        console_level:int = logging.INFO,
        file_level:int = logging.DEBUG,
        log_file = None
)->logging.Logger:   #这个函数返回一个 logging.Logger 类型的对象
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)

    #避免重复添加Handler
    if logger.handlers:
        return logger
    #控制台Handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(console_level)
    console_handler.setFormatter(DEFAULT_LOG_FORMAT)

    logger.addHandler(console_handler)

    # ============================================
    # ✅ 添加文件Handler（关键修改）
    # ============================================
    if log_file:
        # 如果传入了日志文件路径，使用指定路径
        log_path = log_file
    else:
        # 如果没有指定，自动生成带日期的日志文件
        today = datetime.now().strftime("%Y%m%d")
        log_path = os.path.join(LOG_ROOT, f"{name}_{today}.log")

    # 确保日志文件所在目录存在
    os.makedirs(os.path.dirname(log_path), exist_ok=True)

    # 创建文件处理器
    file_handler = logging.FileHandler(log_path, encoding='utf-8')
    file_handler.setLevel(file_level)
    file_handler.setFormatter(DEFAULT_LOG_FORMAT)
    logger.addHandler(file_handler)

    return logger

#快捷获取日志期
logger = get_logger()

if __name__ == '__main__':
    logger.info("信息日志")
    logger.error("错误日志")
    logger.warning("警告日志")
    logger.debug("调试日志")