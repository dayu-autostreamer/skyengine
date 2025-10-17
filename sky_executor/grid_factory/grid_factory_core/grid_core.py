import random
import time
import threading
from sky_executor.grid_factory.grid_factory.grid_factory_env.grid_factory_env import (
    GridFactoryEnv,
)
import config

from backend.service.grid import file_service
from backend.service.grid import agent_service
from sky_executor.utils.thread_pool import ThreadPool
from sky_logs.dc_helper import DiskCacheHelper
from config.all_field_const import CacheInfo
from sky_logs.logger import Logger

LOGGER = Logger(log_path=config.BACKEND_LOG_DIR, name="backend").logger


class GridCore:
    """
    GridCore 用于管理整个仿真系统的生命周期（启动、暂停、恢复、停止等）。
    """

    def __init__(self):
        self.dh = DiskCacheHelper(config.CACHE_DIR, expire=CacheInfo.CACHE_EXPIRE.value)
        # 环境组件
        self.env: GridFactoryEnv = None
        self.agv_agent = None
        self.system_agent = None
        self.hyper_config = None
        self.obs = None
        self.info = None
        # 控制线程
        self.thread_pool = ThreadPool()
        self.sim_thread: threading.Thread = None

        # 控制标志位
        self._stop_event = threading.Event()  # 停止
        self._pause_event = threading.Event()  # 暂停
        self._running_lock = threading.Lock()  # 保证串行
        self._is_running = False

    # -----------------------------
    # 工厂/环境设置接口
    # -----------------------------
    def set_factory(self, factory_name: str = None):
        """根据工厂名称切换当前环境"""
        self.bootstrap(map_name=factory_name)


    # -----------------------------
    # 初始化与环境设置
    # -----------------------------
    def bootstrap(self, **kwargs):
        """初始化环境与智能体"""
        grid_config, job_config, agv_agent_config, system_agent_config, hyper_config = \
            file_service.get_default_config(**kwargs)

        self.env = GridFactoryEnv(grid_config)
        self.agv_agent = agent_service.create_agv_agent(agv_agent_config)
        self.system_agent = agent_service.create_system_policy(system_agent_config)
        self.hyper_config = hyper_config or {}

        self.obs, self.info = self.reset()
        LOGGER.info("[GridCore] 系统初始化完成")

    def reset(self):
        """重置环境"""
        self._stop_event.set()  # 不stop
        self._is_running = False
        obs, info = self.env.reset(seed=self.hyper_config.get('seed', random.randint(0, 10000)))
        return obs, info

    # -----------------------------
    # 仿真主循环
    # -----------------------------
    def _run_loop(self):
        """内部运行循环函数"""
        LOGGER.info("[GridCore] 仿真开始运行")

        step_time = self.hyper_config.get('step_time', 1.0)

        while not self._stop_event.is_set():
            # 若暂停则阻塞等待
            self._pause_event.wait()

            start_time = time.time()

            # 智能体决策
            agent_actions = self.agv_agent.act(self.obs['agent_observation'])
            system_actions = self.system_agent.act(self.obs['machine_observation'])

            # 环境步进
            obs, reward, terminated, truncated, info = self.env.step({
                'agent_actions': agent_actions,
                'machine_actions': system_actions
            })

            if all(terminated['agent_done']) or all(truncated['agent_truncated']):
                LOGGER.info("[GridCore] 仿真已终止")
                break

            # 控制步进速率
            elapsed = time.time() - start_time
            if elapsed < step_time:
                time.sleep(step_time - elapsed)

        LOGGER.info("[GridCore] 仿真线程结束")
        self._is_running = False

    # -----------------------------
    # 控制接口
    # -----------------------------
    def start(self):
        """开始仿真运行"""
        with self._running_lock:
            if self._is_running:
                LOGGER.info("[GridCore] 仿真已在运行中")
                return

            self._stop_event.clear()  # 不stop
            self._pause_event.set()  # 确保开始时不阻塞
            self.sim_thread = threading.Thread(target=self._run_loop, daemon=True)
            self.sim_thread.start()
            self._is_running = True
            LOGGER.info("[GridCore] 仿真线程启动")
        return True

    def pause(self):
        """暂停仿真"""
        if not self._is_running:
            LOGGER.info("[GridCore] 仿真未运行，无法暂停")
            return
        self._pause_event.clear()
        LOGGER.info("[GridCore] 仿真已暂停")
        return True

    def resume(self):
        """恢复仿真"""
        if not self._is_running:
            LOGGER.info("[GridCore] 仿真未运行，无法恢复")
            return
        self._pause_event.set()
        LOGGER.info("[GridCore] 仿真已恢复")
        return True

    def stop(self):
        """停止仿真"""
        if not self._is_running:
            LOGGER.info("[GridCore] 仿真未运行，无法停止")
            return False
        self._stop_event.set()
        self._pause_event.set()  # 防止卡在暂停状态
        LOGGER.info("[GridCore] 仿真停止信号发出")
        return True

    # -----------------------------
    # 可视化接口
    # -----------------------------
    def render_map(self):
        """返回当前环境渲染图"""
        if self.env is None:
            LOGGER.info("[GridCore] 环境未初始化")
            # 刷新环境获得缓存
            self.bootstrap()
        image_svg = self.dh.get(CacheInfo.SVG_IMAGE.value)
        return image_svg

    def get_factory_list(self):
        """返回当前工厂列表"""
        if self.env is None:
            LOGGER.info("[GridCore] 环境未初始化")
            # 刷新环境获得缓存
            self.bootstrap()
        factory_list = self.env.get_maps()
        return factory_list

    def get_job_list(self):
        """返回当前任务列表"""
        if self.env is None:
            LOGGER.info("[GridCore] 环境未初始化")
            # 刷新环境获得缓存
            self.bootstrap()
        job_list = self.env.get_jobs()
        return job_list


if __name__ == '__main__':
    core = GridCore()
    res = core.render_map()
    print(res)
