class NetworkAPIPath:
    # 接口：工厂控制
    FACTORY_ALIVE = '/factory/alive'
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
    JOB_TEMPLATES = '/jobs'
    JOB_ADD = '/job/add/{jobId}'

    # 接口：信息展示
    JOBS_PROGRESS = '/jobs/progress'

    # 接口：上传,下载文件
    YAML_UPLOAD = '/{config_name}/yaml/upload'
    STANDARD_GET = '/standard/get'
    LOG_DOWNLOAD = '/log/download'

    # 获取图片
    MAP_UPDATE='/map/update'
    # 启动系统
    MAP_RENDER='/map/render'
    # 获取工厂列表
    FACTORY_LIST = '/factory/list'

    # 获取案例
    CASES_IMAGE = '/cases/image'
    CASES_CONFIG = '/cases/config'

class NetworkAPIMethod:
    # 接口：工厂控制
    FACTORY_ALIVE = 'GET'
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
    JOB_TEMPLATES = 'GET'
    JOB_ADD = 'POST'

    # 接口：信息展示
    JOBS_PROGRESS = 'GET'

    # 接口：上传,下载文件
    YAML_UPLOAD = 'POST'
    LOG_DOWNLOAD = 'POST'
    STANDARD_GET = 'GET'

    # 获取图片
    MAP_UPDATE='GET'
    # 启动系统
    MAP_RENDER='POST'
    # 获取工厂列表
    FACTORY_LIST = 'GET'

    # 获取案例
    CASES_IMAGE = 'GET'
    CASES_CONFIG = 'GET'
