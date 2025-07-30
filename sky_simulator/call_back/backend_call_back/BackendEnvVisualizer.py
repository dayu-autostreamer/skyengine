import io
import pygame
import os
import cv2
import numpy as np

from sky_simulator.call_back.base_callback.EnvVisualizer import EnvVisualizer
from sky_logs.logger import LOGGER
from sky_simulator.registry import register_component

os.environ["SDL_VIDEODRIVER"] = "dummy"  # 必须放在 pygame.init() 前面


# 仿真环境创建前的初始化
@register_component("backend_callback.Visualizer")
class BackendEnvVisualizer(EnvVisualizer):
    def __init__(self, _fps=3) -> None:
        super().__init__(_fps)

        pygame.font.init()

        self.pic = None

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
