#!/usr/bin/env python3
"""
测试基于Pogema的网格工厂环境
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from pogema import GridConfig
from sky_executor.grid_factory.factory.grid_factory_env.grid_factory_env import GridFactoryEnv

def test_grid_factory_env():
    """测试网格工厂环境"""
    print("=== 测试基于Pogema的网格工厂环境 ===")
    
    # 创建网格配置
    grid_config = GridConfig(
        num_agents=4,           # 4个智能体
        size=15,                # 15x15网格
        density=0.3,            # 30%障碍物密度
        seed=42,                # 随机种子
        max_episode_steps=100,  # 最大步数
        obs_radius=3,           # 观察半径
        collision_system='priority',  # 碰撞系统
        observation_type='POMAPF',      # 观察类型
        on_target='restart'     # 到达目标后重启
    )
    
    print(f"网格配置: {grid_config.num_agents}个智能体, {grid_config.size}x{grid_config.size}网格")
    
    # 创建环境
    env = GridFactoryEnv(
        grid_config=grid_config,
        use_pogema=True,
        env_config={'enable_logging': True}
    )
    
    print("✓ 环境创建成功")
    
    # 测试环境重置
    obs, info = env.reset(seed=42)
    print("✓ 环境重置成功")
    
    # 测试环境步进
    actions = [0, 1, 2, 3]  # 4个智能体的动作
    obs, rewards, terminations, truncations, infos = env.step({'decisions': [], 'step_time': 1.0})
    print("✓ 环境步进成功")
    
    # 获取环境信息
    print(f"智能体位置: {env.get_agent_positions()}")
    print(f"智能体目标: {env.get_agent_targets()}")
    print(f"智能体信息: {env.get_agents_info()}")
    
    # 测试多次步进
    for i in range(5):
        actions = [0, 1, 2, 3]  # 简单的动作
        obs, rewards, terminations, truncations, infos = env.step({'decisions': [], 'step_time': 1.0})
        print(f"步进 {i+1}: 位置 {env.get_agent_positions()}")
    
    print("✓ 多次步进测试成功")
    
    # 测试环境状态
    print(f"环境状态: {env.status}")
    print(f"环境时间: {env.get_env_timeline()}")
    print(f"是否完成: {env.env_is_finished()}")
    
    print("\n=== 测试完成 ===")
    return True

def test_without_pogema():
    """测试不使用Pogema的环境"""
    print("\n=== 测试不使用Pogema的环境 ===")
    
    env = GridFactoryEnv(
        use_pogema=False,
        env_config={'enable_logging': False}
    )
    
    print("✓ 非Pogema环境创建成功")
    
    # 测试重置
    obs, info = env.reset()
    print("✓ 非Pogema环境重置成功")
    
    # 测试步进
    obs, rewards, terminations, truncations, infos = env.step({'decisions': [], 'step_time': 1.0})
    print("✓ 非Pogema环境步进成功")
    
    print("=== 非Pogema测试完成 ===")
    return True

if __name__ == '__main__':
    try:
        # 测试Pogema环境
        test_grid_factory_env()
        
        # 测试非Pogema环境
        test_without_pogema()
        
        print("\n🎉 所有测试通过！")
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()