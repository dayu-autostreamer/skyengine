from typing import List, Tuple

from sky_simulator.call_back.EnvCallback import EnvCallback
from sky_simulator.registry import register_component
import yaml
from sky_simulator.registry import component_registry
from sky_logs.logger import LOGGER


@register_component("backend_callback.GridMapLoader")
class FactoryMapLoader(EnvCallback):
    def __init__(self):
        super().__init__()
        self.env_type = component_registry.get('config').get('env_type')
        self.config = component_registry.get('config').get(self.env_type)
        self.job_config_file_path = self.config.get("task_config").get('file')  # 对应 job_config.yaml
        self.map_config_file_path = self.config.get("factory_config").get('file')  # 对应 map_config.yaml

        map_file = self.map_config_file_path
        map_yaml = yaml.safe_load(open(map_file, 'rb'))
        self.map_config = map_yaml['config']

    def create_jobs(self):
        pass

    def create_graph(self):
        pass

    def create_machines(self):
        pass

    def __call__(self):
        pass


if __name__ == '__main__':
    mapLoader = FactoryMapLoader()
    print(mapLoader())
