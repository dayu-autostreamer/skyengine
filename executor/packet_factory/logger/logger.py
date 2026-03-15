import logging
import os
import time

import executor.packet_factory.logger.system_logs as system_logs
import executor.packet_factory.logger.backend_logs as backend_logs

class Logger:
    def __init__(self, log_path, name):
        # 定义时间戳格式（年-月-日_时-分）
        timestamp_format = "%Y%m%d-%H%M%S"  # 包含秒
        # 获取当前时间并格式化为字符串
        current_time = time.strftime(timestamp_format)

        log_file = os.path.join(log_path, f'{name}_{current_time}.log')

        self.logger = logging.getLogger(name)

        self.format = logging.Formatter(
            '[%(asctime)-15s] %(filename)s(%(lineno)d)'
            ' [%(levelname)s] - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )

        # 控制台输出
        # console_handler = logging.StreamHandler()
        # console_handler.setFormatter(self.format)
        # self.logger.addHandler(console_handler)
        # 文件输出
        os.makedirs(os.path.dirname(log_file), exist_ok=True)  # 自动创建目录
        file_handler = logging.FileHandler(log_file, mode='w', encoding='utf-8')
        file_handler.setFormatter(self.format)
        self.logger.addHandler(file_handler)
        # self.logger.addHandler(console_handler)

        self.logLevel = 'INFO'
        self.logger.setLevel(level=self.logLevel)
        self.logger.propagate = False


# 提供的默认LOGGER会存储到system中去
LOGGER = Logger(log_path=system_logs.dir_path, name="system").logger
BACKEND_LOGGER = Logger(log_path=backend_logs.dir_path, name="backend").logger

if __name__ == '__main__':
    LOGGER.info("233")
    LOGGER.warning("233")
