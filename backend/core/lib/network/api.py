class NetworkAPIPath:
    # 测试接口
    TEST = '/test'

    # 接口：工厂控制
    FACTORY_START = '/factory/start'
    FACTORY_PAUSE = '/factory/pause'
    FACTORY_RESET = '/factory/reset'
    FACTORY_SPEED = '/factory/speed'

    # 接口：AGV 控制
    AGVS = '/agvs'
    AGV_PAUSE = '/agv/pause/{agvId}'
    AGV_RESUME = '/agv/resume/{agvId}'

    # 接口：机器控制
    MACHINES = '/machines'
    MACHINE_PAUSE = '/machine/pause/{machineId}'
    MACHINE_RESUME = '/machine/resume/{machineId}'

    # 接口：Job 控制
    JOBS = '/jobs'
    JOB_ADD = '/job/add/{jobId}'

    # 接口：信息展示
    JOBS_PROGRESS = '/jobs/progress'

    # 接口：上传,下载文件
    YAML_UPLOAD = '/{config_name}/yaml/upload'
    STANDARD_GET = '/standard/get'
    LOG_DOWNLOAD = '/log/download'


class NetworkAPIMethod:
    # 测试接口
    TEST = 'POST'

    # 接口：工厂控制
    FACTORY_START = 'POST'
    FACTORY_PAUSE = 'POST'
    FACTORY_RESET = 'POST'
    FACTORY_SPEED = 'POST'

    # 接口：AGV 控制
    AGVS = 'GET'
    AGV_PAUSE = 'POST'
    AGV_RESUME = 'POST'

    # 接口：机器控制
    MACHINES = 'GET'
    MACHINE_PAUSE = 'POST'
    MACHINE_RESUME = 'POST'

    # 接口：Job 控制
    JOBS = 'GET'
    JOB_ADD = 'POST'

    # 接口：信息展示
    JOBS_PROGRESS = 'GET'

    # 接口：上传,下载文件
    YAML_UPLOAD = 'POST'
    LOG_DOWNLOAD = 'GET'
    STANDARD_GET = 'GET'
