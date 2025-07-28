import io
from typing import List
import pygame
import os
from sky_simulator.call_back.EnvCallback import EnvCallback
from sky_logs.logger import LOGGER
from sky_simulator.registry import register_component
from sky_simulator.packet_factory.packet_factory_env.Job.Job import Job
from sky_simulator.packet_factory.packet_factory_env.Machine.Machine import Machine
from sky_simulator.packet_factory.packet_factory_env.Agv.AGV import AGV
from sky_simulator.packet_factory.packet_factory_env.Job.Operation import Operation
from sky_simulator.packet_factory.packet_factory_env.Utils.util import OperationStatus, MachineStatus, AGVStatus

os.environ["SDL_VIDEODRIVER"] = "dummy"  # 必须放在 pygame.init() 前面


# 仿真环境创建前的初始化
@register_component("backend_callback.Visualizer")
class EnvVisualizer(EnvCallback):
    WIDTH, HEIGHT = 1024, 768

    # 颜色
    WHITE = (255, 255, 255)
    BLACK = (0, 0, 0)

    OPERATION_STATE_COLOR = {
        OperationStatus.WAITING: (240, 240, 240),  # 浅灰 - 等待（更接近白，柔和）
        OperationStatus.READY: (255, 200, 0),  # 浅黄橙 - 就绪
        OperationStatus.MOVING: (255, 150, 0),  # 中橙 - 移动中
        OperationStatus.WORKING: (255, 90, 0),  # 橙红 - 执行中
        OperationStatus.FINISHED: (200, 50, 0),  # 暗红橙 - 完成
        OperationStatus.EXCEPTION: (255, 0, 0)  # 鲜红 - 异常（醒目突出）
    }

    AGV_STATE_COLOR = {
        AGVStatus.READY: (0, 200, 0),  # 鲜绿 - 可用
        AGVStatus.ASSIGNED: (0, 160, 0),  # 中绿 - 已分配
        AGVStatus.LOADED: (0, 120, 0),  # 深绿 - 已装载
        AGVStatus.EXCEPTION: (255, 0, 0)  # 鲜红 - 异常（与正常绿色系强烈对比）
    }

    MACHINE_STATE_COLOR = {
        MachineStatus.READY: (130, 180, 255),  # 浅蓝 - 就绪
        MachineStatus.WORKING: (80, 130, 200),  # 中蓝 - 执行中
        MachineStatus.FAILED: (170, 0, 170),  # 紫红 - 故障
        MachineStatus.EXCEPTION: (255, 0, 0)  # 鲜红 - 异常（与蓝色/紫色形成强对比）
    }

    AGV_SHIFT = (0, -0.10)
    AGV_OPERATION_SHIFT = (0.10, -0.10)
    MACHINE_SHIFT = (0, 0)
    MACHINE_INPUT_SHIFT = (-0.10, 0.12)
    MACHINE_OUTPUT_SHIFT = (0.34, 0.12)

    def __init__(self, _fps=3) -> None:
        super().__init__()
        self.fps = _fps
        self.env = None

        pygame.font.init()

        self.clock = pygame.time.Clock()

        self.should_restart = False
        self.should_pause = False
        self.should_run = False

        self.agv_pause_queue = []
        self.agv_resume_queue = []
        self.machine_pause_queue = []
        self.machine_resume_queue = []
        self.job_add_queue = []

        self.uncertainty_event_queue = []

        self.overall_scale = None
        self.overall_shift = None

        self.pic = None

    def __call__(self):
        """使类的实例可以像函数一样被调用"""
        self.visualize_env()

    def calculate_scale_and_shift(self, left, top, right, bottom):
        all_points = []

        # 收集所有点的位置
        graph = self.env.getGraph()
        for point in graph.points:
            all_points.append((point.x, point.y))
        for machine in self.env.getMachines():
            machine_x, machine_y = machine.get_xy()
            all_points.append((machine_x + self.MACHINE_SHIFT[0], machine_y + self.MACHINE_SHIFT[1]))
            all_points.append((machine_x + self.MACHINE_INPUT_SHIFT[0], machine_y + self.MACHINE_INPUT_SHIFT[1]))
            all_points.append((machine_x + self.MACHINE_OUTPUT_SHIFT[0], machine_y + self.MACHINE_OUTPUT_SHIFT[1]))
        for agv in self.env.getAGVs():
            agv_x, agv_y = agv.get_xy()
            all_points.append((agv_x + self.AGV_SHIFT[0], agv_y + self.AGV_SHIFT[1]))
            all_points.append((agv_x + self.AGV_OPERATION_SHIFT[0], agv_y + self.AGV_OPERATION_SHIFT[1]))

        # 计算边界
        min_x = min(point[0] for point in all_points)
        max_x = max(point[0] for point in all_points)
        min_y = min(point[1] for point in all_points)
        max_y = max(point[1] for point in all_points)

        # 根据窗口大小计算缩放比例
        width_scale = (right - left - 200) / (max_x - min_x)  # 留出边距
        height_scale = (bottom - top - 200) / (max_y - min_y)  # 留出边距

        scale_factor = min(width_scale, height_scale)  # 选择较小的比例以适应窗口

        shift_x = left + 100 - min_x * scale_factor  # 确保最左端有100像素的边距
        shift_y = top + 100 - min_y * scale_factor  # 确保最上端有100像素的边距

        return scale_factor, (shift_x, shift_y)

    def scaling(self, pos, shift=(0, 0)):
        return (int((pos[0] + shift[0]) * self.overall_scale + self.overall_shift[0]),
                int((pos[1] + shift[1]) * self.overall_scale + self.overall_shift[1]))

    def draw_agv(self, screen, agv: AGV):
        color = self.AGV_STATE_COLOR.get(agv.status, self.BLACK)
        position = self.scaling(agv.get_xy(), shift=self.AGV_SHIFT)
        pygame.draw.circle(screen, color, position, int(0.15 * self.overall_scale))
        font = pygame.font.SysFont(None, int(0.24 * self.overall_scale))
        label = font.render(str(agv.id), True, self.WHITE)
        screen.blit(label, (position[0], position[1]))

    def draw_machine(self, screen, machine: Machine):
        color = self.MACHINE_STATE_COLOR.get(machine.status, self.BLACK)
        position = self.scaling(machine.get_xy(), shift=self.MACHINE_SHIFT)
        rect = pygame.Rect(position[0], position[1], int(0.40 * self.overall_scale), int(0.40 * self.overall_scale))
        pygame.draw.rect(screen, color, rect)
        font = pygame.font.SysFont(None, int(0.24 * self.overall_scale))
        label = font.render(str(machine.id), True, self.BLACK)
        screen.blit(label, (position[0], position[1]))

    def draw_operation(self, screen, operation: Operation, position):
        color = self.OPERATION_STATE_COLOR.get(operation.status, self.BLACK)
        rect = pygame.Rect(position[0], position[1], int(0.16 * self.overall_scale), int(0.16 * self.overall_scale))
        pygame.draw.rect(screen, color, rect)
        font = pygame.font.SysFont(None, int(0.2 * self.overall_scale))
        label = font.render(str(operation.id), True, self.WHITE)
        screen.blit(label, (position[0], position[1]))

    def draw_point(self, screen, point):
        pos = self.scaling(point)
        pygame.draw.circle(screen, self.BLACK, pos, int(0.06 * self.overall_scale))

    def draw_link(self, screen, point1, point2):
        pos1 = self.scaling(point1)
        pos2 = self.scaling(point2)
        pygame.draw.line(screen, self.BLACK, pos1, pos2, int(0.02 * self.overall_scale))

    def visualize_env(self, env=None):
        # 渲染
        if self.env is None and env is not None:
            self.env = env

        if self.env is None:
            LOGGER.error("请先初始化环境")

        # 离屏 Surface
        surface = pygame.Surface((self.WIDTH, self.HEIGHT))

        if self.overall_scale is None or self.overall_shift is None:
            self.overall_scale, self.overall_shift = self.calculate_scale_and_shift(0, 0, self.WIDTH, self.HEIGHT)

        surface.fill(self.WHITE)

        # 渲染图结构
        graph = self.env.getGraph()
        for point in graph.points:
            self.draw_point(surface, (point.x, point.y))
        for link in graph.links:
            point1 = graph.get_point_by_id(link.point1)
            point2 = graph.get_point_by_id(link.point2)
            self.draw_link(surface, (point1.x, point1.y), (point2.x, point2.y))

        # 渲染机器和操作
        for machine in self.env.getMachines():
            self.draw_machine(surface, machine)
            for operation in machine.input_queue:
                self.draw_operation(surface, operation, self.scaling(machine.get_xy(), shift=self.MACHINE_INPUT_SHIFT))
            for operation in machine.output_queue:
                self.draw_operation(surface, operation, self.scaling(machine.get_xy(), shift=self.MACHINE_OUTPUT_SHIFT))

        for agv in self.env.getAGVs():
            self.draw_agv(surface, agv)
            agv_operation = agv.get_operation()
            if agv_operation is not None:
                self.draw_operation(surface, agv_operation, self.scaling(agv.get_xy(), shift=self.AGV_OPERATION_SHIFT))

        import cv2
        import numpy as np

        # 将 surface 转换为字符串（字节数组），格式为 RGB
        image_str = pygame.image.tostring(surface, 'RGB')
        width, height = surface.get_size()

        # 转为 NumPy 数组（H, W, C）
        img_np = np.frombuffer(image_str, dtype=np.uint8).reshape((height, width, 3))

        # 编码成 PNG 格式
        success, encoded_image = cv2.imencode('.png', img_np)
        if not success:
            raise RuntimeError("图像编码失败")

        # 转为 BytesIO
        image_bytes = io.BytesIO(encoded_image.tobytes())

        self.pic = image_bytes
        # 注意：Pygame 使用 RGB，而 OpenCV 使用 BGR，所以需要转换一下颜色通道
        # img_cv = cv2.cvtColor(img_np, cv2.COLOR_RGB2BGR)

        # 显示图像
        # cv2.imshow("Map", img_cv)
        # cv2.waitKey(0)
        # cv2.destroyAllWindows()
        
        self.clock.tick(self.fps)

    def get_map(self):
        """获取地图"""
        if self.pic is None:
            self.visualize_env()

        return self.pic

    def restart(self):
        self.should_restart = True

    def shouldRestart(self) -> bool:
        """
        :return: True if env should restart
        """
        should_restart = self.should_restart
        self.should_restart = False
        return should_restart

    def pause(self):
        self.should_pause = True

    def shouldPause(self) -> bool:
        """
        :return: True if env should pause
        """
        should_pause = self.should_pause
        self.should_pause = False
        return should_pause

    def run(self):
        self.should_run = True

    def shouldRun(self) -> bool:
        """
        :return: True if env should running
        """
        should_run = self.should_run
        self.should_run = False
        return should_run

    def change_speed(self, speed: int):
        self.fps = speed

    def pause_agv(self, agv_id: int):
        """暂停指定AGV运行"""
        for agv in self.env.getAGVs():
            if agv.get_id() == agv_id:
                self.agv_pause_queue.append(agv)
                self.insertNewUncertaintyEvent(f"AGV {agv_id} paused!")
                break

    def getPausedAGVs(self) -> List[AGV]:
        """
        :return: 距离上次调用, 哪些AGV被暂停了
        """
        agv_pause_queue = self.agv_pause_queue
        self.agv_pause_queue = []
        return agv_pause_queue

    def resume_agv(self, agv_id: int):
        """恢复指定AGV运行"""
        for agv in self.env.getAGVs():
            if agv.get_id() == agv_id:
                self.agv_resume_queue.append(agv)
                self.insertNewUncertaintyEvent(f"AGV {agv_id} resumed!")
                break

    def getResumedAGVs(self) -> List[AGV]:
        """
        :return: 距离上次调用, 哪些AGV被恢复运行了
        """
        agv_resume_queue = self.agv_resume_queue
        self.agv_resume_queue = []
        return agv_resume_queue

    def pause_machine(self, machine_id: int):
        """暂停指定 Machine"""
        for machine in self.env.getMachines():
            if machine.get_id() == machine_id:
                self.machine_pause_queue.append(machine)
                self.insertNewUncertaintyEvent(f"Machine {machine_id} paused!")
                break

    def getPausedMachines(self) -> List[Machine]:
        """
        :return: 距离上次调用, 哪些Machine被暂停了
        """
        machine_pause_queue = self.machine_pause_queue
        self.machine_pause_queue = []
        return machine_pause_queue

    def resume_machine(self, machine_id: int):
        """恢复指定 Machine"""
        for machine in self.env.getMachines():
            if machine.get_id() == machine_id:
                self.machine_resume_queue.append(machine)
                self.insertNewUncertaintyEvent(f"Machine {machine_id} resumed!")
                break

    def getResumedMachines(self) -> List[Machine]:
        """
        :return: 距离上次调用, 哪些Machine被恢复运行了
        """
        machine_resume_queue = self.machine_resume_queue
        self.machine_resume_queue = []
        return machine_resume_queue

    def add_job(self, job_id: int):
        """添加指定 Job"""
        for job in self.env.getJobs():
            if job.get_id() == job_id:
                self.job_add_queue.append(job.clone())
                self.insertNewUncertaintyEvent(f"Job {job_id} added!")
                break

    def getAddedJobs(self) -> List[Job]:
        """
        :return: 距离上次调用, 哪些Job被添加了
        """
        job_add_queue = self.job_add_queue
        self.job_add_queue = []
        return job_add_queue

    def insertNewUncertaintyEvent(self, event: str):
        self.uncertainty_event_queue.append(event)

    def getNewUncertaintyEvents(self) -> List[str]:
        """
        :return: 距离上次调用, 哪些新的不确定性事件发生了, 以字符串形式format后传递, 最后将由visualizer直接显示
        """
        result = self.uncertainty_event_queue
        self.uncertainty_event_queue = []
        return result

    def getBuffered(self):
        """
        :return: [
                {
                    event_type: "packet_factory.ENV_PAUSED" / "packet_factory.AGV_FAIL" / ...
                    event_method: "trigger" / "recover"
                    type: "" / "AGV" / "Machine" / "Job" 
                    data: None / AGV / Machine / Job 实例
                }
                ]
        """
        result = []

        if self.shouldRestart():
            result.append({
                "event_type": "packet_factory.ENV_RESTART",
                "event_method": "trigger",
                "type": "",
                "data": None
            })

        if self.shouldPause():
            result.append({
                "event_type": "packet_factory.ENV_PAUSED",
                "event_method": "trigger",
                "type": "",
                "data": None
            })

        if self.shouldRun():
            result.append({
                "event_type": "packet_factory.ENV_RECOVER",
                "event_method": "trigger",
                "type": "",
                "data": None
            })

        for paused_agv in self.getPausedAGVs():
            result.append({
                "event_type": "packet_factory.AGV_FAIL",
                "event_method": "trigger",
                "type": "AGV",
                "data": paused_agv,
            })

        for resumed_agv in self.getResumedAGVs():
            result.append({
                "event_type": "packet_factory.AGV_FAIL",
                "event_method": "recover",
                "type": "AGV",
                "data": resumed_agv,
            })

        for paused_machine in self.getPausedMachines():
            result.append({
                "event_type": "packet_factory.MACHINE_FAIL",
                "event_method": "trigger",
                "type": "MACHINE",
                "data": paused_machine,
            })

        for resumed_machine in self.getResumedMachines():
            result.append({
                "event_type": "packet_factory.MACHINE_FAIL",
                "event_method": "recover",
                "type": "MACHINE",
                "data": resumed_machine,
            })

        for added_job in self.getAddedJobs():
            result.append({
                "event_type": "packet_factory.JOB_ADD",
                "event_method": "trigger",
                "type": "JOB",
                "data": added_job,
            })

        return result
