from dataclasses import dataclass


@dataclass(frozen=True)
class Endpoint:
    path: str
    method: str


class GridAPI:
    """重构后的接口统一管理类，所有接口通过Endpoint封装路径与请求方法"""
    # ------------------------------ 0. 工厂环境切换接口 ------------------------------
    MANAGE_FACTORY = Endpoint(
        path="/manage",
        method="POST"
    )
    # ------------------------------ 1. 工厂控制接口 ------------------------------
    FACTORY_ALIVE = Endpoint(
        path="/factory/alive",
        method="GET"
    )
    FACTORY_START = Endpoint(
        path="/factory/start",
        method="POST"
    )
    FACTORY_PAUSE = Endpoint(
        path="/factory/pause",
        method="POST"
    )
    FACTORY_RESUME = Endpoint(
        path="/factory/resume",
        method="POST"
    )
    FACTORY_RESET = Endpoint(
        path="/factory/reset",
        method="POST"
    )
    FACTORY_SPEED = Endpoint(
        path="/factory/speed",
        method="POST"
    )
    FACTORY_LIST = Endpoint(
        path="/factory/list",
        method="GET"
    )
    # ------------------------------ 2. AGV控制接口 ------------------------------
    AGVS = Endpoint(
        path="/agvs",
        method="GET"
    )
    AGV_MONITOR = Endpoint(
        path="/monitor/agv",
        method="GET"
    )

    # ------------------------------ 3. 机器控制接口 ------------------------------
    MACHINES = Endpoint(
        path="/machines",
        method="GET"
    )
    MACHINE_MONITOR = Endpoint(
        path="/monitor/machine",
        method="GET"
    )

    # ------------------------------ 4. Job控制接口 ------------------------------
    JOB_TEMPLATES = Endpoint(
        path="/job",
        method="GET"
    )
    JOB_ADD = Endpoint(
        path="/job/add/{jobId}",  # 路径参数：jobId（指定作业ID）
        method="POST"
    )
    JOBS_PROGRESS = Endpoint(
        path="/job/progress",
        method="GET"
    )
    JOB_MONITOR = Endpoint(
        path="/monitor/job",
        method="GET"
    )
    JOB_LIST = Endpoint(
        path="/job/list",
        method="GET"
    )
    # ------------------------------ 5. 地图相关接口 ------------------------------
    MAP_UPDATE = Endpoint(
        path="/map/update",
        method="GET"
    )
    MAP_RENDER = Endpoint(
        path="/map/render",
        method="POST"
    )

    # ------------------------------ 6. 文件上传/下载接口 ------------------------------
    YAML_UPLOAD = Endpoint(
        path="/{config_name}/yaml/upload",  # 路径参数：config_name（配置名称）
        method="POST"
    )
    STANDARD_GET = Endpoint(
        path="/standard/get",
        method="GET"
    )
    LOG_DOWNLOAD = Endpoint(
        path="/log/download",
        method="POST"
    )

    # ------------------------------ 7. 案例相关接口 ------------------------------
    CASES_IMAGE = Endpoint(
        path="/cases/image",
        method="GET"
    )
    CASES_CONFIG = Endpoint(
        path="/cases/config",
        method="GET"
    )
    CASES_PREVIEW = Endpoint(
        path="/cases/preview/",
        method="GET"
    )

    # ------------------------------ 8. Agent管理接口 ------------------------------
    AGENT_LIST = Endpoint(
        path="/Agent/list",
        method="GET"
    )
    SET_AGENT = Endpoint(
        path="/Agent/set",
        method="POST"
    )

    # ------------------------------ 9. 系统监控接口 ------------------------------
    SYSTEM_MONITOR = Endpoint(
        path="/monitor/system",
        method="GET"
    )
    TOTAL_MONITOR = Endpoint(
        path="/monitor/total",
        method="GET"
    )


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
    MAP_UPDATE = '/map/update'
    # 启动系统
    MAP_RENDER = '/map/render'
    # 获取工厂列表
    FACTORY_LIST = '/factory/list'

    # 获取案例
    CASES_IMAGE = '/cases/image'
    CASES_CONFIG = '/cases/config'

    # ========== AGENT相关操作 ==========
    # 获取Agent
    AGENT_LIST = '/Agent/list'
    SET_AGENT = '/Agent/set'

    # ========== MONITOR相关操作 ==========
    AGV_MONITOR = '/monitor/agv'
    MACHINE_MONITOR = '/monitor/machine'
    JOB_MONITOR = '/monitor/job'
    SYSTEM_MONITOR = '/monitor/system'
    TOTAL_MONITOR = '/monitor/total'


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
    MAP_UPDATE = 'GET'
    # 启动系统
    MAP_RENDER = 'POST'
    # 获取工厂列表
    FACTORY_LIST = 'GET'

    # 获取案例
    CASES_IMAGE = 'GET'
    CASES_CONFIG = 'GET'

    # 获取支持的Agent列表
    AGENT_LIST = 'GET'
    SET_AGENT = 'POST'

    AGV_MONITOR = 'GET'
    MACHINE_MONITOR = 'GET'
    JOB_MONITOR = 'GET'
    SYSTEM_MONITOR = 'GET'
    TOTAL_MONITOR = 'GET'
