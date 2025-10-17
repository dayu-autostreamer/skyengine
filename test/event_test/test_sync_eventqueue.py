"""
同步EventQueue与EventGenerator集成测试
"""

import time
import sys
import os

# 添加项目根目录到路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from sky_executor.utils.event.event_manager.EventManager import EventManager
from sky_executor.utils.call_back.base_callback.EventQueue import EventQueue


def test_sync_eventqueue_basic():
    """测试基本的同步EventQueue功能"""
    print("=== 测试基本同步EventQueue ===")
    
    # 创建事件管理器并加载配置
    event_manager = EventManager()
    config_path = os.path.join(os.path.dirname(__file__), '../../config/template_config_set/event_config.yaml')
    event_manager.load_event(config_path)
    
    # 创建集成的EventQueue
    event_queue = EventQueue(event_manager=event_manager)
    
    # 设置生成间隔
    event_queue.set_generation_interval(0.5)
    
    print("开始同步测试，运行10秒...")
    
    # 模拟环境设置
    class MockEnv:
        def __init__(self):
            self.name = "MockEnvironment"
    
    mock_env = MockEnv()
    event_queue.set_env(mock_env)
    
    # 运行一段时间
    start_time = time.time()
    while time.time() - start_time < 10:
        # 调用EventQueue处理事件
        ready_events = event_queue()
        
        if ready_events:
            print(f"处理了 {len(ready_events)} 个事件")
            for event in ready_events:
                print(f"  - {event}")
        
        time.sleep(0.1)
    
    # 获取统计信息
    stats = event_queue.get_generation_stats()
    print(f"\n统计信息:")
    print(f"  总处理事件数: {stats['total_events_processed']}")
    print(f"  总生成事件数: {stats['total_events_generated']}")
    print(f"  队列大小: {stats['queue_size']}")
    print(f"  按类型统计: {stats['events_by_type']}")
    
    if 'generator_stats' in stats:
        gen_stats = stats['generator_stats']
        print(f"  生成器统计: {gen_stats}")
    
    print("基本同步测试完成")


def test_sync_eventqueue_manual_config():
    """测试手动配置的同步EventQueue"""
    print("\n=== 测试手动配置同步EventQueue ===")
    
    # 创建事件管理器
    event_manager = EventManager()
    event_manager.add_event('packet_factory.AGV_FAIL')
    event_manager.add_event('packet_factory.MACHINE_FAIL')
    event_manager.add_event('packet_factory.JOB_ADD')
    
    # 创建EventQueue
    event_queue = EventQueue(event_manager=event_manager)
    
    # 手动添加事件配置
    event_queue.add_event_config(
        event_type='packet_factory.AGV_FAIL',
        probability=0.3,
        strategy='uniform'
    )
    
    event_queue.add_event_config(
        event_type='packet_factory.MACHINE_FAIL',
        probability=0.2,
        strategy='poisson'
    )
    
    event_queue.add_event_config(
        event_type='packet_factory.JOB_ADD',
        probability=0.4,
        strategy='exponential'
    )
    
    # 设置生成间隔
    event_queue.set_generation_interval(0.3)
    
    # 模拟环境设置
    class MockEnv:
        def __init__(self):
            self.name = "MockEnvironment"
    
    mock_env = MockEnv()
    event_queue.set_env(mock_env)
    
    print("手动配置测试，运行8秒...")
    
    # 运行一段时间
    start_time = time.time()
    while time.time() - start_time < 8:
        ready_events = event_queue()
        
        if ready_events:
            print(f"处理了 {len(ready_events)} 个事件")
        
        time.sleep(0.1)
    
    # 获取统计信息
    stats = event_queue.get_generation_stats()
    print(f"\n统计信息:")
    print(f"  总处理事件数: {stats['total_events_processed']}")
    print(f"  总生成事件数: {stats['total_events_generated']}")
    print(f"  队列大小: {stats['queue_size']}")
    
    print("手动配置测试完成")


def test_sync_eventqueue_queue_management():
    """测试同步EventQueue的队列管理功能"""
    print("\n=== 测试队列管理功能 ===")
    
    # 创建事件管理器
    event_manager = EventManager()
    event_manager.add_event('packet_factory.AGV_FAIL')
    
    # 创建EventQueue
    event_queue = EventQueue(event_manager=event_manager)
    
    # 添加高概率事件配置
    event_queue.add_event_config(
        event_type='packet_factory.AGV_FAIL',
        probability=0.8,  # 高概率
        strategy='uniform'
    )
    
    # 设置较短的生成间隔
    event_queue.set_generation_interval(0.1)
    
    # 模拟环境设置
    class MockEnv:
        def __init__(self):
            self.name = "MockEnvironment"
    
    mock_env = MockEnv()
    event_queue.set_env(mock_env)
    
    print("高概率事件生成，运行3秒...")
    
    # 运行一段时间
    start_time = time.time()
    while time.time() - start_time < 3:
        ready_events = event_queue()
        if ready_events:
            print(f"处理了 {len(ready_events)} 个事件")
        time.sleep(0.1)
    
    # 检查队列状态
    print(f"队列大小: {len(event_queue)}")
    print(f"下一个事件时间: {event_queue.peek_next_event()}")
    
    # 清空队列
    print("清空队列...")
    event_queue.clear_queue()
    print(f"清空后队列大小: {len(event_queue)}")
    
    # 重置统计
    print("重置统计...")
    event_queue.reset_stats()
    stats = event_queue.get_generation_stats()
    print(f"重置后总事件数: {stats['total_events_processed']}")
    
    print("队列管理测试完成")


def test_sync_eventqueue_performance():
    """测试同步EventQueue的性能"""
    print("\n=== 测试性能 ===")
    
    # 创建事件管理器
    event_manager = EventManager()
    event_manager.add_event('packet_factory.AGV_FAIL')
    event_manager.add_event('packet_factory.MACHINE_FAIL')
    event_manager.add_event('packet_factory.JOB_ADD')
    
    # 创建EventQueue
    event_queue = EventQueue(event_manager=event_manager)
    
    # 添加事件配置
    event_queue.add_event_config('packet_factory.AGV_FAIL', probability=0.1, strategy='uniform')
    event_queue.add_event_config('packet_factory.MACHINE_FAIL', probability=0.1, strategy='uniform')
    event_queue.add_event_config('packet_factory.JOB_ADD', probability=0.1, strategy='uniform')
    
    # 设置生成间隔
    event_queue.set_generation_interval(0.05)  # 高频生成
    
    # 模拟环境设置
    class MockEnv:
        def __init__(self):
            self.name = "MockEnvironment"
    
    mock_env = MockEnv()
    event_queue.set_env(mock_env)
    
    print("性能测试，运行5秒...")
    
    # 性能测试
    start_time = time.time()
    total_events = 0
    iterations = 0
    
    while time.time() - start_time < 5:
        ready_events = event_queue()
        if ready_events:
            total_events += len(ready_events)
        iterations += 1
        time.sleep(0.01)  # 高频调用
    
    end_time = time.time()
    duration = end_time - start_time
    
    print(f"性能统计:")
    print(f"  运行时间: {duration:.2f} 秒")
    print(f"  总迭代次数: {iterations}")
    print(f"  处理事件数: {total_events}")
    print(f"  平均每秒迭代: {iterations/duration:.2f}")
    print(f"  平均每秒事件: {total_events/duration:.2f}")
    
    # 最终统计
    stats = event_queue.get_generation_stats()
    print(f"  队列大小: {stats['queue_size']}")
    print(f"  总生成事件数: {stats['total_events_generated']}")
    
    print("性能测试完成")


if __name__ == "__main__":
    print("同步EventQueue与EventGenerator集成测试开始")
    print("=" * 60)
    
    try:
        # 运行各种测试
        test_sync_eventqueue_basic()
        test_sync_eventqueue_manual_config()
        test_sync_eventqueue_queue_management()
        test_sync_eventqueue_performance()
        
        print("\n" + "=" * 60)
        print("所有同步测试完成！")
        
    except Exception as e:
        print(f"测试过程中出现错误: {e}")
        import traceback
        traceback.print_exc()

