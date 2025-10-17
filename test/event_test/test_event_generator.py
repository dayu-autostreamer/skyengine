"""
EventGenerator 使用示例和测试
"""

import time
import sys
import os

# 添加项目根目录到路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from sky_executor.utils.event.event_manager.EventManager import EventManager
from sky_executor.utils.event import EventGenerator, EventGenerationStrategy


def test_basic_event_generation():
    """测试基本的事件生成功能"""
    print("=== 测试基本事件生成 ===")
    
    # 创建事件管理器
    event_manager = EventManager()
    
    # 添加支持的事件类型
    event_manager.add_event('packet_factory.AGV_FAIL')
    event_manager.add_event('packet_factory.MACHINE_FAIL')
    event_manager.add_event('packet_factory.JOB_ADD')
    
    # 创建事件生成器
    generator = EventGenerator(event_manager)
    
    # 添加事件配置
    generator.add_event_config(
        event_type='packet_factory.AGV_FAIL',
        probability=0.1,
        strategy=EventGenerationStrategy.UNIFORM
    )
    
    generator.add_event_config(
        event_type='packet_factory.MACHINE_FAIL',
        probability=0.05,
        strategy=EventGenerationStrategy.POISSON
    )
    
    generator.add_event_config(
        event_type='packet_factory.JOB_ADD',
        probability=0.2,
        strategy=EventGenerationStrategy.EXPONENTIAL
    )
    
    # 开始生成事件
    generator.start_generation(time_step=0.5)
    
    # 运行一段时间
    print("开始生成事件，运行10秒...")
    time.sleep(10)
    
    # 获取统计信息
    stats = generator.get_generation_stats()
    print(f"生成统计: {stats}")
    
    # 获取生成的事件
    events = generator.get_next_events(max_count=20)
    print(f"生成了 {len(events)} 个事件")
    
    for event in events:
        print(f"  - {event}")
    
    # 停止生成
    generator.stop_generation()
    print("事件生成已停止")


def test_config_file_loading():
    """测试从配置文件加载"""
    print("\n=== 测试配置文件加载 ===")
    
    # 创建事件管理器
    event_manager = EventManager()
    
    # 添加支持的事件类型
    event_manager.add_event('packet_factory.AGV_FAIL')
    event_manager.add_event('packet_factory.MACHINE_FAIL')
    event_manager.add_event('packet_factory.JOB_ADD')
    event_manager.add_event('packet_factory.ENV_PAUSED')
    event_manager.add_event('packet_factory.ENV_RECOVER')
    
    # 从配置文件创建事件生成器
    config_path = os.path.join(os.path.dirname(__file__), '../../config/event_generator_config.yaml')
    generator = EventGenerator(event_manager, config_path)
    
    # 开始生成事件
    generator.start_generation()
    
    # 运行一段时间
    print("从配置文件加载，运行15秒...")
    time.sleep(15)
    
    # 获取统计信息
    stats = generator.get_generation_stats()
    print(f"生成统计: {stats}")
    
    # 停止生成
    generator.stop_generation()
    print("事件生成已停止")


def test_custom_payload_generator():
    """测试自定义payload生成器"""
    print("\n=== 测试自定义payload生成器 ===")
    
    # 创建事件管理器
    event_manager = EventManager()
    event_manager.add_event('packet_factory.JOB_ADD')
    
    # 创建事件生成器
    generator = EventGenerator(event_manager)
    
    # 自定义payload生成器
    def custom_job_payload():
        return {
            'job': {
                'id': f"JOB_{int(time.time())}",
                'priority': 1,
                'deadline': time.time() + 300,
                'custom_field': 'test_value'
            }
        }
    
    # 添加事件配置，使用自定义payload生成器
    generator.add_event_config(
        event_type='packet_factory.JOB_ADD',
        probability=0.3,
        strategy=EventGenerationStrategy.UNIFORM,
        payload_generator=custom_job_payload
    )
    
    # 开始生成事件
    generator.start_generation(time_step=1.0)
    
    # 运行一段时间
    print("使用自定义payload生成器，运行5秒...")
    time.sleep(5)
    
    # 获取生成的事件
    events = generator.get_next_events(max_count=10)
    print(f"生成了 {len(events)} 个事件")
    
    for event in events:
        print(f"  - {event}")
        print(f"    Payload: {event.payload}")
    
    # 停止生成
    generator.stop_generation()
    print("事件生成已停止")


def test_event_queue_management():
    """测试事件队列管理"""
    print("\n=== 测试事件队列管理 ===")
    
    # 创建事件管理器
    event_manager = EventManager()
    event_manager.add_event('packet_factory.AGV_FAIL')
    
    # 创建事件生成器
    generator = EventGenerator(event_manager)
    
    # 添加高概率事件配置
    generator.add_event_config(
        event_type='packet_factory.AGV_FAIL',
        probability=0.8,  # 高概率
        strategy=EventGenerationStrategy.UNIFORM
    )
    
    # 开始生成事件
    generator.start_generation(time_step=0.1)
    
    # 运行一段时间
    print("高概率事件生成，运行3秒...")
    time.sleep(3)
    
    # 检查队列大小
    stats = generator.get_generation_stats()
    print(f"队列大小: {stats['queue_size']}")
    
    # 分批获取事件
    batch1 = generator.get_next_events(max_count=5)
    print(f"第一批获取了 {len(batch1)} 个事件")
    
    batch2 = generator.get_next_events(max_count=5)
    print(f"第二批获取了 {len(batch2)} 个事件")
    
    # 清空队列
    generator.clear_queue()
    stats_after_clear = generator.get_generation_stats()
    print(f"清空后队列大小: {stats_after_clear['queue_size']}")
    
    # 停止生成
    generator.stop_generation()
    print("事件生成已停止")


if __name__ == "__main__":
    print("EventGenerator 测试开始")
    print("=" * 50)
    
    try:
        # 运行各种测试
        test_basic_event_generation()
        test_config_file_loading()
        test_custom_payload_generator()
        test_event_queue_management()
        
        print("\n" + "=" * 50)
        print("所有测试完成！")
        
    except Exception as e:
        print(f"测试过程中出现错误: {e}")
        import traceback
        traceback.print_exc()
