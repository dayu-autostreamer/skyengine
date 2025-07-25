import logging
import os

from sky_simulator import get_project_root

class Logger:
    def __init__(self, name: str = None):
        log_file = os.path.join(get_project_root(), 'logs', 'myapp.log')

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

        self.logLevel = 'INFO'
        self.logger.setLevel(level=self.logLevel)
        self.logger.propagate = False


LOGGER = Logger().logger

if __name__ == '__main__':
    LOGGER.info("233")
    LOGGER.warning("233")
