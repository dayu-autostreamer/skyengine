from typing import List
import pygame
import pygame_gui
from pygame_gui import UIManager
from pygame_gui.elements import UIButton, UIDropDownMenu, UILabel, UITextBox, UIProgressBar, UIScrollingContainer

from sky_simulator.call_back.EnvCallback import EnvCallback
from sky_simulator.registry import register_component
from sky_simulator.packet_factory.packet_factory_env.Graph.Job import Job
from sky_simulator.packet_factory.packet_factory_env.Graph.Machine import Machine
from sky_simulator.packet_factory.packet_factory_env.Graph.AGV import AGV
from sky_simulator.packet_factory.packet_factory_env.Graph.Operation import Operation
from sky_simulator.packet_factory.packet_factory_env.Graph.util import OperationStatus, MachineStatus, AGVStatus
from sky_simulator.packet_factory.packet_factory_env.Utils.logger import LOGGER


def scale(pos, scale=(80, 100), shift=(100, 100)):
    return (int(pos[0] * scale[0] + shift[0]), int(pos[1] * scale[1] + shift[1]))


# 仿真环境创建前的初始化
@register_component("packet_factory.Visualizer")
class EnvVisualizer(EnvCallback):
    WIDTH, HEIGHT = 1024, 768

    # 颜色
    WHITE = (255, 255, 255)
    BLACK = (0, 0, 0)

    OPERATION_STATE_COLOR = {
        OperationStatus.WAITING: (240, 240, 240),     # 浅灰 - 等待（更接近白，柔和）
        OperationStatus.READY: (255, 200, 0),         # 浅黄橙 - 就绪
        OperationStatus.MOVING: (255, 150, 0),        # 中橙 - 移动中
        OperationStatus.WORKING: (255, 90, 0),        # 橙红 - 执行中
        OperationStatus.FINISHED: (200, 50, 0),       # 暗红橙 - 完成
        OperationStatus.EXCEPTION: (255, 0, 0)        # 鲜红 - 异常（醒目突出）
    }

    AGV_STATE_COLOR = {
        AGVStatus.READY: (0, 200, 0),         # 鲜绿 - 可用
        AGVStatus.ASSIGNED: (0, 160, 0),      # 中绿 - 已分配
        AGVStatus.LOADED: (0, 120, 0),        # 深绿 - 已装载
        AGVStatus.EXCEPTION: (255, 0, 0)      # 鲜红 - 异常（与正常绿色系强烈对比）
    }

    MACHINE_STATE_COLOR = {
        MachineStatus.READY: (130, 180, 255),     # 浅蓝 - 就绪
        MachineStatus.WORKING: (80, 130, 200),    # 中蓝 - 执行中
        MachineStatus.FAILED: (170, 0, 170),      # 紫红 - 故障
        MachineStatus.EXCEPTION: (255, 0, 0)      # 鲜红 - 异常（与蓝色/紫色形成强对比）
    }

    def __init__(self, _fps=3) -> None:
        super().__init__()
        self.fps = _fps
        self.env = None
        pygame.init()
        self.screen = pygame.display.set_mode((self.WIDTH, self.HEIGHT))

        # 初始化UI管理器
        self.ui_manager = UIManager((self.WIDTH, self.HEIGHT))

        self.clock = pygame.time.Clock()
        
        self.running = False
        self.restart = False

        self.agv_pause_queue = []
        self.agv_resume_queue = []
        self.machine_pause_queue = []
        self.machine_resume_queue = []
        self.job_add_queue = []
    
    def _init_env(self, env):
        self.env = env
        # 创建按钮和下拉菜单
        self.create_ui_elements(self.env.getAGVs(), self.env.getMachines(), self.env.getJobs())

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

    def draw_agv_ui(self, right_panel_x, dropdown_pos_y, agvs: List[AGV]):
        # AGV 暂停/恢复对应按钮 + 下拉菜单
        agv_list = [f"AGV{agv.get_id()}" for agv in agvs]
        self.selected_agv_id = agvs[0].get_id()
        self.agv_dropdown = UIDropDownMenu(
            options_list=agv_list,
            starting_option=agv_list[0],
            relative_rect=pygame.Rect((right_panel_x, dropdown_pos_y), (150, 40)),
            manager=self.ui_manager
        )
        self.agv_pause_button = UIButton(
            relative_rect=pygame.Rect((right_panel_x + 160, dropdown_pos_y), (80, 40)),
            text='Pause',
            manager=self.ui_manager
        )
        self.agv_resume_button = UIButton(
            relative_rect=pygame.Rect((right_panel_x + 250, dropdown_pos_y), (80, 40)),
            text='Resume',
            manager=self.ui_manager
        )

    def draw_machine_ui(self, right_panel_x, dropdown_pos_y, machines: List[Machine]):
        # Machine 暂停/恢复对应按钮 + 下拉菜单
        machine_list = [f"Machine{machine.get_id()}" for machine in machines]
        self.selected_machine_id = machines[0].get_id()
        self.machine_dropdown = UIDropDownMenu(
            options_list=machine_list,
            starting_option=machine_list[0],
            relative_rect=pygame.Rect((right_panel_x, dropdown_pos_y), (150, 40)),
            manager=self.ui_manager
        )
        self.machine_pause_button = UIButton(
            relative_rect=pygame.Rect((right_panel_x + 160, dropdown_pos_y), (80, 40)),
            text='Pause',
            manager=self.ui_manager
        )
        self.machine_resume_button = UIButton(
            relative_rect=pygame.Rect((right_panel_x + 250, dropdown_pos_y), (80, 40)),
            text='Resume',
            manager=self.ui_manager
        )
    
    def draw_job_ui(self, right_panel_x, dropdown_pos_y, jobs: List[Job]):
        # Job 新增
        job_list = [f"Job{job.get_id()}" for job in jobs]
        self.selected_job_id = jobs[0].get_id()
        self.job_type_dropdown = UIDropDownMenu(
            options_list=job_list,
            starting_option=job_list[0],
            relative_rect=pygame.Rect((right_panel_x, dropdown_pos_y), (150, 40)),
            manager=self.ui_manager
        )
        self.add_job_button = UIButton(
            relative_rect=pygame.Rect((right_panel_x + 160, dropdown_pos_y), (80, 40)),
            text='Add',
            manager=self.ui_manager
        )

    def draw_job_progress_ui(self, jobs: List[Job]):
        # 创建滚动区域的 Rect
        scroll_rect = pygame.Rect(20, 450, 500, 300)

        # 创建 UIScrollingContainer 容器
        self.job_progress_scroll_container = UIScrollingContainer(
            relative_rect=scroll_rect,
            manager=self.ui_manager
        )

        # 保存每个 Job 的当前进度值（从 0 开始）
        self.job_progress = [0.0 for _ in range(len(jobs))]

        # 添加 Job 标签和进度条到滚动内容中
        self.job_progress_bars = []
        self.job_progress_labels = []

        for i, job in enumerate(jobs):
            job_name = f"Job {job.get_id()}"
            label = UILabel(
                relative_rect=pygame.Rect(0, i * 30, 100, 30),
                text=job_name,
                manager=self.ui_manager,
                container=self.job_progress_scroll_container
            )
            bar = UIProgressBar(
                relative_rect=pygame.Rect(110, i * 30, 380, 20),
                manager=self.ui_manager,
                container=self.job_progress_scroll_container
            )
            self.job_progress_labels.append(label)
            self.job_progress_bars.append(bar)

        # 设置滚动容器的内容大小（必须设置，否则无法滚动）
        self.job_progress_scroll_container.set_scrollable_area_dimensions((500, len(self.job_progress_bars) * 30))

    def update_job_progress(self, jobs: List[Job]):
        """
        Job 进度更新
        """
        self.job_progress_scroll_container.kill()
        self.draw_job_progress_ui(jobs)
        for i, job in enumerate(jobs):
            self.job_progress[i] = job.get_progress() * 100.0
            self.job_progress_bars[i].set_current_progress(self.job_progress[i])

    def draw_uncertainty_event_ui(self):
        # 滚动容器的位置和大小
        scroll_container_rect = pygame.Rect((530, 450), (470, 300))

        # 创建 UIScrollingContainer
        self.uncertainty_event_scroll_container = UIScrollingContainer(
            relative_rect=scroll_container_rect,
            manager=self.ui_manager
        )

        # 创建一个足够大的 UITextBox 放入滚动容器中
        log_text_rect = pygame.Rect(0, 0, 450, 300)

        self.uncertainty_event_log_textbox = UITextBox(
            html_text="",
            relative_rect=log_text_rect,
            manager=self.ui_manager,
            container=self.uncertainty_event_scroll_container
        )

    def add_uncertainty_event_log(self, message):
        new_log = f"{message}<br>"
        
        # 更新日志文本
        self.uncertainty_event_log_textbox.html_text += new_log
        
        # 重新构建 UI 元素以应用更改
        self.uncertainty_event_log_textbox.rebuild()

    def create_ui_elements(self, agvs: List[AGV], machines: List[Machine], jobs: List[Job]):
        # 右侧控制按钮区域
        button_size = (100, 40)
        right_panel_x = 650  # 超出左侧800px的可用区域
        top_y = 40

        # 开始、暂停、重启按钮
        self.start_button = UIButton(
            relative_rect=pygame.Rect((right_panel_x, top_y), button_size),
            text='Start',
            manager=self.ui_manager
        )
        self.pause_button = UIButton(
            relative_rect=pygame.Rect((right_panel_x, top_y + button_size[1] + 10), button_size),
            text='Pause',
            manager=self.ui_manager
        )
        self.restart_button = UIButton(
            relative_rect=pygame.Rect((right_panel_x, top_y + 2 * (button_size[1] + 10)), button_size),
            text='Restart',
            manager=self.ui_manager
        )

        # AGV/Machine 暂停/恢复
        dropdown_pos_y = top_y + 3 * (button_size[1] + 10)
        self.draw_agv_ui(right_panel_x, dropdown_pos_y, agvs)

        # Machine 暂停/恢复
        dropdown_pos_y += 50
        self.draw_machine_ui(right_panel_x, dropdown_pos_y, machines)
        
        # Job 新增
        dropdown_pos_y += 50
        self.draw_job_ui(right_panel_x, dropdown_pos_y, jobs)
        
        # 左下 Job 进度显示
        self.draw_job_progress_ui(jobs)

        # 右下 不确定性事件日志窗口（可滚动）
        self.draw_uncertainty_event_ui()
        
    def visualize_env(self, env=None):
        # 渲染
        if self.env is None and env is not None:
            self._init_env(env)

        if self.env is None:
            LOGGER.error("请先初始化环境")

        self.screen.fill(self.WHITE)

        # 处理GUI事件
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            self.ui_manager.process_events(event)

            if event.type == pygame.USEREVENT:
                if event.user_type == pygame_gui.UI_BUTTON_PRESSED:
                    if event.ui_element == self.start_button:
                        self.running = True
                        print("Start Button Pressed")
                    elif event.ui_element == self.pause_button:
                        self.running = False
                        print("Pause Button Pressed")
                    elif event.ui_element == self.restart_button:
                        self.restart = True
                        print("Restart Button Pressed")
                    elif event.ui_element == self.agv_pause_button:
                        self.pause_agv(self.selected_agv_id)
                    elif event.ui_element == self.agv_resume_button:
                        self.resume_agv(self.selected_agv_id)
                    elif event.ui_element == self.machine_pause_button:
                        self.pause_machine(self.selected_machine_id)
                    elif event.ui_element == self.machine_resume_button:
                        self.resume_machine(self.selected_machine_id)
                    elif event.ui_element == self.add_job_button:
                        self.add_job(self.selected_job_id)

                elif event.user_type == pygame_gui.UI_DROP_DOWN_MENU_CHANGED:
                    if event.ui_element == self.agv_dropdown:
                        # 处理 AGV 下拉菜单选择变化
                        self.selected_agv_id = int(event.text[3:])  # 假设选项是 "AGV1", "AGV2" 这种格式
                        print(f"Selected AGV ID: {self.selected_agv_id}")
                    elif event.ui_element == self.machine_dropdown:
                        # 处理 Machine 下拉菜单选择变化
                        self.selected_machine_id = int(event.text[7:])  # 假设选项是 "Machine1", "Machine2"
                        print(f"Selected Machine ID: {self.selected_machine_id}")
                    elif event.ui_element == self.job_type_dropdown:
                        # 处理 Job 下拉菜单选择变化
                        self.selected_job_id = int(event.text[3:])  # 假设选项是 "Job1", "Job2"
                        print(f"Selected Job ID: {self.selected_job_id}")

        self.update_job_progress(self.env.getJobs())

        uncertainty_events = self.env.getNewUncertaintyEvents()
        if uncertainty_events:
            for event in uncertainty_events:
                self.add_uncertainty_event_log(f"{event}")

        # 更新GUI
        self.ui_manager.update(self.clock.tick(self.fps)/1000.0)

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


        # 绘制GUI
        self.ui_manager.draw_ui(self.screen)

        pygame.display.flip()
        self.clock.tick(self.fps)


    def shouldRestart(self) -> bool:
        """
        :return: True if env should restart
        """
        restart = self.restart
        self.restart = False
        return restart

    def isRunning(self) -> bool:
        """
        :return: True if env should running
        """
        return self.running

    def pause_agv(self, agv_id: int):
        """暂停指定AGV运行"""
        for agv in self.env.getAGVs():
            if agv.get_id() == agv_id:
                self.agv_pause_queue.append(agv)
                print(f"AGV {agv_id} paused")
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
                print(f"AGV {agv_id} resumed")
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
                print(f"Machine {machine_id} paused")
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
                print(f"Machine {machine_id} resumed")
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
                self.job_add_queue.append(job)
                print(f"Job {job_id} added")
                break
    
    def getAddedJobs(self) -> List[Job]:
        """
        :return: 距离上次调用, 哪些Job被添加了
        """
        job_add_queue = self.job_add_queue
        self.job_add_queue = []
        return job_add_queue
