'''
@Project ：tiangong 
@File    ：test_agv.py
@IDE     ：PyCharm 
@Author  ：Skyrim
@Date    ：2025/9/21 0:01 
'''
from tiangong_simulator.call_back.callback_manager.AGVCallbackManager import AGVCallbackManager


def test_agv():
    callback_manager = AGVCallbackManager()
    res=callback_manager.use_all_after_work()
    return res

if __name__ == '__main__':
    res=test_agv()
    print(res)




