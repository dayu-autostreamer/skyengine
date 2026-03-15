from typing import List
import pygame
import pygame_gui
from pygame_gui import UIManager
from pygame_gui.elements import UIButton, UIDropDownMenu, UILabel, UITextBox, UIProgressBar, UIScrollingContainer

from executor.packet_factory.call_back.base_callback.EnvVisualizer import EnvVisualizer
from executor.packet_factory.logger.logger import LOGGER
from executor.packet_factory.registry import register_component
from executor.packet_factory.packet_factory.packet_factory_env.Job.Job import Job
from executor.packet_factory.packet_factory.packet_factory_env.Machine.Machine import Machine
from executor.packet_factory.packet_factory.packet_factory_env.Agv.AGV import AGV


# 仿真环境创建前的初始化
@register_component("packet_factory_callback.InteractiveVisualizer")
class InteractiveVisualizer(EnvVisualizer):
    def __init__(self, _fps=3) -> None:
        super().__init__(_fps)
        
        # 初始化UI管理器
        self.ui_manager = UIManager((self.WIDTH, self.HEIGHT))


    def _init_env(self, env):
        self.env = env
        # 创建按钮和下拉菜单
        self.create_ui_elements(self.env.getAGVs(), self.env.getMachines(), self.env.getJobs())


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

        # 设置滚动容器的内容大小
        content_height = len(self.job_progress_bars) * 30
        self.job_progress_scroll_container.set_scrollable_area_dimensions((500, content_height))

        # 滚动到底部
        self.job_progress_scroll_container.vert_scroll_bar.set_scroll_from_start_percentage(1)

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
            
        if self.overall_scale is None or self.overall_shift is None:
            self.overall_scale, self.overall_shift = self.calculate_scale_and_shift(0, 0, 700, 500)

        self.screen.fill(self.WHITE)

        # 处理GUI事件
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                # TODO: 插入退出环境的事件
                pass
            self.ui_manager.process_events(event)

            if event.type == pygame.USEREVENT:
                if event.user_type == pygame_gui.UI_BUTTON_PRESSED:
                    if event.ui_element == self.start_button:
                        self.should_run = True
                        self.insertNewUncertaintyEvent("Start!")
                    elif event.ui_element == self.pause_button:
                        self.should_pause = True
                        self.insertNewUncertaintyEvent("Pause!")
                    elif event.ui_element == self.restart_button:
                        self.restart = True
                        self.insertNewUncertaintyEvent("Restart!")
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

        uncertainty_events = self.getNewUncertaintyEvents()
        if uncertainty_events:
            for event in uncertainty_events:
                self.add_uncertainty_event_log(f"{event}")

        # 更新GUI
        self.ui_manager.update(self.clock.tick(self.fps) / 1000.0)

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
                self.draw_operation(self.screen, operation, self.scaling(machine.get_xy(), shift=self.MACHINE_INPUT_SHIFT))
            for operation in machine.output_queue:
                self.draw_operation(self.screen, operation, self.scaling(machine.get_xy(), shift=self.MACHINE_OUTPUT_SHIFT))

        for agv in self.env.getAGVs():
            self.draw_agv(self.screen, agv)
            agv_operation = agv.get_operation()
            if agv_operation is not None:
                self.draw_operation(self.screen, agv_operation, self.scaling(agv.get_xy(), shift=self.AGV_OPERATION_SHIFT))


        # 绘制GUI
        self.ui_manager.draw_ui(self.screen)

        pygame.display.flip()
        self.clock.tick(self.fps)
