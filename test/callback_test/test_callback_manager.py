'''
@Project ：tiangong 
@File    ：test_callback_manager.py
@IDE     ：PyCharm 
@Author  ：Skyrim
@Date    ：2025/9/21 0:41 
'''
import config
from sky_executor.utils.call_back import JobCallbackManager
from sky_executor.packet_factory.lifecycle import bootstrap
from sky_executor.utils.registry import component_registry, create_component_by_id

if __name__ == '__main__':
    # 为了测试config，执行bootstrap就会自动创建config
    config_path = config.CONFIG_DIR + "/application_config.yaml"
    env, agent = bootstrap(config_path)

    env_type = component_registry.get('config').get('env_type')
    config = component_registry.get('config').get(env_type)

    job_callback_manager = JobCallbackManager()
    after_work_configs = config.get("callback").get("job_callback").get("after_work").get("name")
    print(after_work_configs)

    for callback_name in after_work_configs:
        job_callback_manager.add_callback_to_group('after_work', create_component_by_id(callback_name))

    job_callback_manager.use_all_after_work("233")