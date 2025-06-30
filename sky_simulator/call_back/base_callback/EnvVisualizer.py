from typing import List
import pygame

from sky_simulator.call_back.EnvCallback import EnvCallback
from sky_simulator.registry import register_component
from sky_simulator.packet_factory.packet_factory_env.Graph.Job import Job
from sky_simulator.packet_factory.packet_factory_env.Graph.Machine import Machine
from sky_simulator.packet_factory.packet_factory_env.Graph.AGV import AGV
from sky_simulator.packet_factory.packet_factory_env.Graph.Operation import Operation
from sky_simulator.packet_factory.packet_factory_env.Graph.util import OperationStatus, MachineStatus, AGVStatus


def scale(pos, scale=(100, 100), shift=(100, 100)):
    return (int(pos[0] * scale[0] + shift[0]), int(pos[1] * scale[1] + shift[1]))


# 仿真环境创建前的初始化
@register_component("base_callback.Visualizer")
class EnvVisualizer(EnvCallback):
    WIDTH, HEIGHT = 800, 600

    # 颜色
    WHITE = (255, 255, 255)
    BLACK = (0, 0, 0)

    OPERATION_STATE_COLOR = {
        OperationStatus.WAITING: (230, 230, 230),  # 浅灰 - 等待
        OperationStatus.READY: (255, 160, 0),  # 橙色 - 就绪
        OperationStatus.MOVING: (255, 100, 0),  # 深橙 - 移动中
        OperationStatus.WORKING: (255, 50, 0),  # 红橙 - 执行中
        OperationStatus.FINISHED: (200, 0, 0),  # 暗红 - 完成
        OperationStatus.EXCEPTION: (139, 0, 0)  # 深红 - 异常
    }

    AGV_STATE_COLOR = {
        AGVStatus.READY: (0, 180, 0),  # 鲜绿 - 可用
        AGVStatus.ASSIGNED: (0, 140, 0),  # 中绿 - 已分配
        AGVStatus.LOADED: (0, 100, 0),  # 深绿 - 已装载
        AGVStatus.EXCEPTION: (0, 60, 0)  # 极深绿 - 异常
    }

    MACHINE_STATE_COLOR = {
        MachineStatus.READY: (100, 100, 255),  # 浅蓝 - 就绪
        MachineStatus.WORKING: (70, 70, 200),  # 中蓝 - 执行中
        MachineStatus.FAILED: (139, 0, 139),  # 紫色 - 故障
        MachineStatus.EXCEPTION: (100, 0, 100)  # 深紫 - 异常
    }

    def __init__(self, _fps=3) -> None:
        super().__init__()
        self.fps = _fps
        self.env = None
        pygame.init()
        self.screen = pygame.display.set_mode((self.WIDTH, self.HEIGHT))
        self.clock = pygame.time.Clock()

    def __call__(self):
        """使类的实例可以像函数一样被调用"""
        self.visualize_env()

    def draw_agv(self, screen, agv: AGV):
        color = self.AGV_STATE_COLOR.get(agv.status, self.BLACK)
        position = scale(agv.get_xy(), shift=(100, 90))
        pygame.draw.circle(screen, color, position, 15)
        font = pygame.font.SysFont(None, 24)
        label = font.render(str(agv.id), True, self.WHITE)
        screen.blit(label, (position[0], position[1]))

    def draw_machine(self, screen, machine: Machine):
        color = self.MACHINE_STATE_COLOR.get(machine.status, self.BLACK)
        position = scale(machine.get_xy())
        rect = pygame.Rect(position[0], position[1], 40, 40)
        pygame.draw.rect(screen, color, rect)
        font = pygame.font.SysFont(None, 24)
        label = font.render(str(machine.id), True, self.BLACK)
        screen.blit(label, (position[0], position[1]))

    def draw_operation(self, screen, operation: Operation, position):
        color = self.OPERATION_STATE_COLOR.get(operation.status, self.BLACK)
        rect = pygame.Rect(position[0], position[1], 16, 16)
        pygame.draw.rect(screen, color, rect)
        font = pygame.font.SysFont(None, 24)
        label = font.render(str(operation.id), True, self.WHITE)
        screen.blit(label, (position[0], position[1]))

    def draw_point(self, screen, point):
        pos = scale(point)
        pygame.draw.circle(screen, self.BLACK, pos, 6)

    def draw_link(self, screen, point1, point2):
        pos1 = scale(point1)
        pos2 = scale(point2)
        pygame.draw.line(screen, self.BLACK, pos1, pos2, 2)

    def visualize_env(self, env=None):
        # 渲染
        if self.env is None and env is not None:
            self.env = env
        if self.env is None:
            LOGGER.error("请先初始化环境")

        self.screen.fill(self.WHITE)

        graph = self.env.getGraph()
        for point in graph.points:
            self.draw_point(self.screen, (point.x, point.y))
        for link in graph.links:
            point1 = graph.get_point_by_id(link.point1)
            point2 = graph.get_point_by_id(link.point2)
            self.draw_link(self.screen, (point1.x, point1.y), (point2.x, point2.y))

        for machine in self.env.getMachines():
            self.draw_machine(self.screen, machine)
            for operation in machine.input_queue:
                self.draw_operation(self.screen, operation, scale(machine.get_xy(), shift=(90, 110)))
            for operation in machine.output_queue:
                self.draw_operation(self.screen, operation, scale(machine.get_xy(), shift=(130, 110)))

        for agv in self.env.getAGVs():
            self.draw_agv(self.screen, agv)
            agv_operation = agv.get_operation()
            if agv_operation is not None:
                self.draw_operation(self.screen, agv_operation, scale(agv.get_xy(), shift=(110, 90)))


        pygame.display.flip()
        self.clock.tick(self.fps)


    def shouldRestart(self) -> bool:
        """
        :return: True if env should restart
        """
        pass

    def isRunning() -> bool:
        """
        :return: True if env should running
        """
        pass

    def getPausedAGVs(self) -> List[AGV]:
        """
        :return: 距离上次调用, 哪些AGV被暂停了
        """
        pass

    def getResumedAGVs(self) -> List[AGV]:
        """
        :return: 距离上次调用, 哪些AGV被恢复运行了
        """
        pass

    def getPausedMachines(self) -> List[Machine]:
        """
        :return: 距离上次调用, 哪些Machine被暂停了
        """
        pass
    
    def getResumedMachines(self) -> List[Machine]:
        """
        :return: 距离上次调用, 哪些Machine被恢复运行了
        """
        pass
    
    def getAddedJobs(self) -> List[Job]:
        """
        :return: 距离上次调用, 哪些Job被添加了
        """
        pass
