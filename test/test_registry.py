'''
@Project ：tiangong 
@File    ：test_registry.py
@IDE     ：PyCharm 
@Author  ：Skyrim
@Date    ：2025/5/31 0:43 
'''
# bootstrap.py
from sky_simulator.registry import scan_and_register_components, get_component_class_by_id,component_registry,create_component_by_id

def test_scan():
    print("[Bootstrap] Scanning and registering components...")
    scan_and_register_components()


if __name__ == '__main__':
    test_scan()
    print(component_registry)
    agv = get_component_class_by_id("sim_agv")(id_=10,x=1,y=2,velocity=233)
    print(agv)