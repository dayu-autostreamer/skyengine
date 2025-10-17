"""
EventQueue与EventGenerator集成测试
"""

import time
import sys
import os

# 添加项目根目录到路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from sky_executor.utils.event.event_manager.EventManager import EventManager
from sky_executor.utils.call_back.base_callback.EventQueue import EventQueue
from sky_executor.utils.event import EventGenerationStrategy


def test_basic_integration():
    """测试基本的EventQueue与EventGenerator集成"""
    print("=== 测试基本集成 ===")
    
    # 创建事件管理器
    event_manager = EventManager()
    event_manager.add_event('packet_factory.AGV_FAIL')
    event_manager.add_event('packet_factory.MACHINE_FAIL')
    event_manager.add_event('packet_factory.JOB_ADD')
    
    # 创建集成的EventQueue
    event_queue = EventQueue(
        event_manager=event_manager,
        auto_generation=True
    )
    
    # 添加事件生成配置
    event_queue.add_event_config(
        event_type='packet_factory.AGV_FAIL',
        probability=0.2,
        strategy=EventGenerationStrategy.UNIFORM
    )
    
    event_queue.add_event_config(
        event_type='packet_factory.MACHINE_FAIL',
        probability=0.1,
        strategy=EventGenerationStrategy.POISSON
    )
    
    event_queue.add_event_config(
        event_type='packet_factory.JOB_ADD',
        probability=0.3,
        strategy=EventGenerationStrategy.EXPONENTIAL
    )
    
    # 设置生成间隔
    event_queue.set_generation_interval(0.5)
    
    print("开始集成测试，运行10秒...")
    
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
    
    print("基本集成测试完成")


def test_config_file_integration():
    """测试从配置文件加载的集成"""
    print("\n=== 测试配置文件集成 ===")
    
    # 创建事件管理器
    event_manager = EventManager()
    event_manager.add_event('packet_factory.AGV_FAIL')
    event_manager.add_event('packet_factory.MACHINE_FAIL')
    event_manager.add_event('packet_factory.JOB_ADD')
    event_manager.add_event('packet_factory.ENV_PAUSED')
    event_manager.add_event('packet_factory.ENV_RECOVER')
    
    # 从配置文件创建EventQueue
    config_path = os.path.join(os.path.dirname(__file__), '../../config/event_generator_config.yaml')
    event_queue = EventQueue(
        event_manager=event_manager,
        auto_generation=True,
        generation_config_path=config_path
    )
    
    # 模拟环境设置
    class MockEnv:
        def __init__(self):
            self.name = "MockEnvironment"
    
    mock_env = MockEnv()
    event_queue.set_env(mock_env)
    
    print("从配置文件加载，运行15秒...")
    
    # 运行一段时间
    start_time = time.time()
    while time.time() - start_time < 15:
        ready_events = event_queue()
        
        if ready_events:
            print(f"处理了 {len(ready_events)} 个事件")
        
        time.sleep(0.2)
    
    # 获取统计信息
    stats = event_queue.get_generation_stats()
    print(f"\n统计信息:")
    print(f"  总处理事件数: {stats['total_events_processed']}")
    print(f"  总生成事件数: {stats['total_events_generated']}")
    print(f"  队列大小: {stats['queue_size']}")
    print(f"  按类型统计: {stats['events_by_type']}")
    
    print("配置文件集成测试完成")


def test_manual_control():
    """测试手动控制事件生成"""
    print("\n=== 测试手动控制 ===")
    
    # 创建事件管理器
    event_manager = EventManager()
    event_manager.add_event('packet_factory.AGV_FAIL')
    
    # 创建EventQueue，初始禁用自动生成
    event_queue = EventQueue(
        event_manager=event_manager,
        auto_generation=False
    )
    
    # 模拟环境设置
    class MockEnv:
        def __init__(self):
            self.name = "MockEnvironment"
    
    mock_env = MockEnv()
    event_queue.set_env(mock_env)
    
    print("初始状态 - 禁用自动生成")
    stats = event_queue.get_generation_stats()
    print(f"自动生成状态: {stats['auto_generation_enabled']}")
    
    # 手动启用自动生成
    print("手动启用自动生成...")
    event_queue.enable_auto_generation()
    
    # 添加事件配置
    event_queue.add_event_config(
        event_type='packet_factory.AGV_FAIL',
        probability=0.5,
        strategy=EventGenerationStrategy.UNIFORM
    )
    
    # 运行一段时间
    print("运行5秒...")
    start_time = time.time()
    while time.time() - start_time < 5:
        ready_events = event_queue()
        if ready_events:
            print(f"处理了 {len(ready_events)} 个事件")
        time.sleep(0.1)
    
    # 禁用自动生成
    print("禁用自动生成...")
    event_queue.disable_auto_generation()
    
    # 再运行一段时间
    print("禁用后运行3秒...")
    start_time = time.time()
    while time.time() - start_time < 3:
        ready_events = event_queue()
        if ready_events:
            print(f"处理了 {len(ready_events)} 个事件")
        time.sleep(0.1)
    
    # 最终统计
    stats = event_queue.get_generation_stats()
    print(f"\n最终统计:")
    print(f"  总处理事件数: {stats['total_events_processed']}")
    print(f"  自动生成状态: {stats['auto_generation_enabled']}")
    
    print("手动控制测试完成")


def test_queue_management():
    """测试队列管理功能"""
    print("\n=== 测试队列管理 ===")
    
    # 创建事件管理器
    event_manager = EventManager()
    event_manager.add_event('packet_factory.AGV_FAIL')
    
    # 创建EventQueue
    event_queue = EventQueue(
        event_manager=event_manager,
        auto_generation=True
    )
    
    # 添加高概率事件配置
    event_queue.add_event_config(
        event_type='packet_factory.AGV_FAIL',
        probability=0.8,  # 高概率
        strategy=EventGenerationStrategy.UNIFORM
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


if __name__ == "__main__":
    print("EventQueue与EventGenerator集成测试开始")
    print("=" * 60)
    
    try:
        # 运行各种测试
        test_basic_integration()
        test_config_file_integration()
        test_manual_control()
        test_queue_management()
        
        print("\n" + "=" * 60)
        print("所有集成测试完成！")
        
    except Exception as e:
        print(f"测试过程中出现错误: {e}")
        import traceback
        traceback.print_exc()

