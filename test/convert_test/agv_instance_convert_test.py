
# 测试转化后的数据格式能否正常启动系统

from dataset.convert.convert import generate_job_config
from sky_executor.packet_factory.lifecycle import bootstrap

if __name__ == '__main__':
    generate_job_config()
    bootstrap()
