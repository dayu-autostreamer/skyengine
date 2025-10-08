'''
@Project ：SkyEngine 
@File    ：EventGenerator.py
@IDE     ：PyCharm
@Author  ：SkyrimForest
@Date    ：2025/9/30 22:42
'''
import math
import random
import time
from typing import Dict, List, Optional, Any
from collections import defaultdict
from dataclasses import dataclass
from enum import Enum

from sky_simulator.event.event.BaseEvent import BaseEvent
from sky_simulator.event.event_manager.EventManager import EventManager
from sky_logs.logger import LOGGER


class EventGenerationStrategy(Enum):
    """事件生成策略枚举"""
    UNIFORM = "uniform"  # 均匀分布
    BERNOULLI = "bernoulli"  # 伯努利分布
    GEOMETRIC = "geometric"  # 几何分布
    POISSON = "poisson"  # 泊松分布
    CUSTOM = "custom"  # 自定义分布


@dataclass
class EventGenerationConfig:
    """事件生成配置"""
    event_type: str
    probability: float = 0.1
    strategy: EventGenerationStrategy = EventGenerationStrategy.UNIFORM
    min_interval: float = 1.0  # 最小生成间隔(秒)
    max_interval: float = 10.0  # 最大生成间隔(秒)
    burst_probability: float = 0.05  # 突发事件概率
    burst_multiplier: int = 3  # 突发事件倍数
    payload_generator: Optional[callable] = None  # 自定义payload生成器
    conditions: Optional[Dict[str, Any]] = None  # 生成条件


@dataclass
class EventGenerationState:
    """事件生成状态"""
    last_generation_time: float = -10.0  # 上次生成时间
    generation_count: int = 0  # 生成次数
    burst_count: int = 0  # 突发事件计数
    is_active: bool = True  # 是否激活
    cooldown_until: float = 0.0  # 冷却结束时间

    # 用于统计和几何分布
    check_count: int = 0  # 检查次数（每次调用should_generate_event都会增加）
    consecutive_failures: int = 0  # 连续失败次数（用于几何分布）
    last_check_time: float = 0.0  # 上次检查时间
    success_rate: float = 0.0  # 成功率（generation_count / check_count）


class EventGenerator:
    """
    同步事件生成器 - 按时间片和概率生成各种事件
    
    功能特性:
    1. 支持多种概率分布的事件生成
    2. 支持事件生成策略配置
    3. 记录各种事件状态以判断是否应该生成
    """

    def __init__(self):
        """
        初始化事件生成器
        
        Args:
            event_manager: 事件管理器实例
        """
        # 事件生成配置
        self.event_configs: Dict[str, EventGenerationConfig] = {}
        # 每个事件类型的生成状态, 用于记录生成次数、上次生成时间、生成状态、冷却时间
        self.event_states: Dict[str, EventGenerationState] = {}
        # 全局统计信息
        self.generation_stats = {
            'total_events': 0,
            'events_by_type': defaultdict(int),
            'generation_times': [],
            'last_generation_time': 0.0
        }
        # 保证全局的生成间隔
        self.global_generation_interval = 0.1  # 100ms
        self.last_global_generation_time = 0.0

    def add_event_config(self, event_type: str, probability: float = 0.1,
                         strategy: EventGenerationStrategy = EventGenerationStrategy.UNIFORM,
                         min_interval: float = 1.0, max_interval: float = 10.0,
                         burst_probability: float = 0.05, burst_multiplier: int = 3,
                         payload_generator: Optional[callable] = None,
                         conditions: Optional[Dict[str, Any]] = None):
        """
        添加事件生成配置
        
        Args:
            event_type: 事件类型
            probability: 生成概率
            strategy: 生成策略
            min_interval: 最小生成间隔
            max_interval: 最大生成间隔
            burst_probability: 突发事件概率
            burst_multiplier: 突发事件倍数
            payload_generator: 自定义payload生成器
            conditions: 生成条件
        """
        config = EventGenerationConfig(
            event_type=event_type,
            probability=probability,
            strategy=strategy,
            min_interval=min_interval,
            max_interval=max_interval,
            burst_probability=burst_probability,
            burst_multiplier=burst_multiplier,
            payload_generator=payload_generator,
            conditions=conditions
        )

        self.event_configs[event_type] = config
        # 为每个事件类型初始化生成状态
        self.event_states[event_type] = EventGenerationState()
        LOGGER.info(f"[EventGenerator] 添加事件配置: {event_type}")

    def should_generate_event(self, event_type: str, current_time: float) -> bool:
        """
        判断是否应该生成指定类型的事件
        
        Args:
            event_type: 事件类型
            current_time: 当前时间
            
        Returns:
            bool: 是否应该生成事件
        """
        print("==============================")
        print(f"开始进行{event_type}事件的生成")
        if event_type not in self.event_configs or event_type not in self.event_states:
            return False

        config = self.event_configs[event_type]
        state = self.event_states[event_type]

        # 更新检查统计
        state.check_count += 1
        state.last_check_time = current_time

        # 检查事件是否激活
        if not state.is_active:
            state.consecutive_failures += 1
            return False

        # 检查冷却时间
        if current_time < state.cooldown_until:
            state.consecutive_failures += 1
            return False

        # 检查最小生成间隔
        if current_time - state.last_generation_time < config.min_interval:
            state.consecutive_failures += 1
            return False

        # 检查生成条件
        if config.conditions:
            if not self._check_conditions(config.conditions):
                state.consecutive_failures += 1
                return False

        # 根据策略计算生成概率
        should_generate = False
        if config.strategy == EventGenerationStrategy.UNIFORM.value or config.strategy == EventGenerationStrategy.BERNOULLI.value:
            should_generate = random.random() < config.probability

        elif config.strategy == EventGenerationStrategy.POISSON.value:
            # 泊松分布: P(X=k) = (λ^k * e^(-λ)) / k!
            lambda_param = config.probability * 10  # 调整参数
            p = 1 - math.exp(-lambda_param)
            should_generate = random.random() < p

        elif config.strategy == EventGenerationStrategy.GEOMETRIC.value:
            # 几何分布: P(X=k) = (1-p)^(k-1) * p
            # 连续失败k次后，第k+1次成功的概率
            # 这里实现为：连续失败次数越多，下次成功的概率越高
            if state.consecutive_failures == 0:
                geometric_prob = 1 - config.probability
                should_generate = random.random() < geometric_prob
            else:
                # 几何分布：失败次数越多，成功概率越高
                geometric_prob = 1 - (1 - config.probability) ** (state.consecutive_failures + 1)
                should_generate = random.random() < geometric_prob

        elif config.strategy == EventGenerationStrategy.CUSTOM.value:
            # 自定义策略，这里可以实现更复杂的逻辑
            should_generate = random.random() < config.probability

        # 更新连续失败计数
        if should_generate:
            state.consecutive_failures = 0
        else:
            state.consecutive_failures += 1
        return should_generate

    def _check_conditions(self, conditions: Dict[str, Any]) -> bool:
        """检查事件生成条件"""
        # 这里可以实现更复杂的条件检查逻辑
        return True

    def generate_event_payload(self, event_type: str, env_info: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        生成事件payload
        
        Args:
            event_type: 事件类型
            env_info: 环境信息，包含agvs、machines、jobs等信息
            
        Returns:
            Dict: 事件payload
        """
        config = self.event_configs.get(event_type)
        if not config:
            return {}

        # 使用自定义payload生成器
        if config.payload_generator:
            return config.payload_generator(env_info)
        
        try:
            # 解析事件类型，支持多种格式
            # 例如: "packet_factory.AGV_FAIL", "grid_factory.MACHINE_ERROR", "job_system.JOB_ADD"
            event_parts = event_type.split('.')
            if len(event_parts) >= 2:
                module_name = event_parts[0]  # packet_factory, grid_factory, job_system
                event_name = event_parts[-1]  # AGV_FAIL, MACHINE_ERROR, JOB_ADD
                
                # 解析事件对象类型
                event_object = self._parse_event_object(event_name)
                
                if event_object == 'AGV':
                    payload = self._generate_agv_payload(event_name, env_info)
                elif event_object == 'MACHINE':
                    payload = self._generate_machine_payload(event_name, env_info)
                elif event_object == 'JOB':
                    payload = self._generate_job_payload(event_name, env_info)
                else:
                    # 未知事件类型，生成基础payload
                    payload = self._generate_default_payload(event_type, env_info)
            else:
                # 简单事件类型，生成基础payload
                payload = self._generate_default_payload(event_type, env_info)
                
        except Exception as e:
            LOGGER.warning(f"[EventGenerator] 生成payload失败 {event_type}: {e}")
            payload = {'error': str(e), 'event_type': event_type}

        return payload

    def _parse_event_object(self, event_name: str) -> str:
        """
        解析事件对象类型
        
        Args:
            event_name: 事件名称，如 "AGV_FAIL", "MACHINE_ERROR", "JOB_ADD"
            
        Returns:
            str: 对象类型，如 "AGV", "MACHINE", "JOB"
        """
        # 定义事件对象关键词映射
        object_keywords = {
            'AGV': ['AGV', 'AGV_'],
            'MACHINE': ['MACHINE', 'MACHINE_', 'MACH_'],
            'JOB': ['JOB', 'JOB_', 'TASK', 'TASK_'],
            'ROBOT': ['ROBOT', 'ROBOT_', 'ROB_'],
            'VEHICLE': ['VEHICLE', 'VEH_', 'CAR_']
        }
        
        event_name_upper = event_name.upper()
        
        for obj_type, keywords in object_keywords.items():
            for keyword in keywords:
                if event_name_upper.startswith(keyword):
                    return obj_type
                    
        return 'UNKNOWN'

    def _generate_agv_payload(self, event_name: str, env_info: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """生成AGV相关事件的payload"""
        payload = {}
        
        if env_info and 'agvs' in env_info:
            agvs_info = env_info['agvs']
            if isinstance(agvs_info, list) and len(agvs_info) > 0:
                # 从实际AGV列表中选择
                agv_id = random.choice(agvs_info)['id'] if isinstance(agvs_info[0], dict) else random.choice(agvs_info)
            else:
                agv_id = random.randint(1, 10)
        else:
            agv_id = random.randint(1, 10)  # 默认假设有10个AGV
            
        payload['id'] = agv_id
        
        # 根据事件类型添加特定信息
        if 'FAIL' in event_name.upper():
            payload['failure_type'] = random.choice(['mechanical', 'electrical', 'communication', 'sensor'])
            payload['severity'] = random.choice(['low', 'medium', 'high', 'critical'])
        elif 'MOVE' in event_name.upper():
            payload['destination'] = (random.randint(0, 100), random.randint(0, 100))
            payload['speed'] = random.uniform(0.5, 2.0)
            
        return payload

    def _generate_machine_payload(self, event_name: str, env_info: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """生成机器相关事件的payload"""
        payload = {}
        
        if env_info and 'machines' in env_info:
            machines_info = env_info['machines']
            if isinstance(machines_info, list) and len(machines_info) > 0:
                # 从实际机器列表中选择
                machine_id = random.choice(machines_info)['id'] if isinstance(machines_info[0], dict) else random.choice(machines_info)
            else:
                machine_id = random.randint(1, 5)
        else:
            machine_id = random.randint(1, 5)  # 默认假设有5台机器
            
        payload['id'] = machine_id
        
        # 根据事件类型添加特定信息
        if 'FAIL' in event_name.upper() or 'ERROR' in event_name.upper():
            payload['error_code'] = random.randint(1000, 9999)
            payload['error_message'] = random.choice([
                'Temperature sensor malfunction',
                'Motor overload detected',
                'Communication timeout',
                'Calibration error'
            ])
        elif 'STATUS' in event_name.upper():
            payload['status'] = random.choice(['idle', 'working', 'maintenance', 'error'])
            payload['efficiency'] = random.uniform(0.5, 1.0)
            
        return payload

    def _generate_job_payload(self, event_name: str, env_info: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """生成作业相关事件的payload"""
        payload = {}
        
        if 'ADD' in event_name.upper() or 'CREATE' in event_name.upper():
            job_id = random.randint(1000, 9999)
            payload['job'] = {
                'id': job_id,
                'priority': random.randint(1, 5),
                'deadline': time.time() + random.randint(100, 1000),
                'type': random.choice(['manufacturing', 'assembly', 'inspection', 'transport']),
                'complexity': random.choice(['simple', 'medium', 'complex']),
                'estimated_duration': random.randint(30, 300)  # 秒
            }
        elif 'COMPLETE' in event_name.upper() or 'FINISH' in event_name.upper():
            if env_info and 'jobs' in env_info:
                jobs_info = env_info['jobs']
                if isinstance(jobs_info, list) and len(jobs_info) > 0:
                    job_id = random.choice(jobs_info)['id'] if isinstance(jobs_info[0], dict) else random.choice(jobs_info)
                else:
                    job_id = random.randint(1000, 9999)
            else:
                job_id = random.randint(1000, 9999)
                
            payload['job_id'] = job_id
            payload['completion_time'] = time.time()
            payload['quality_score'] = random.uniform(0.7, 1.0)
            
        return payload

    def _generate_default_payload(self, event_type: str, env_info: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """生成默认payload"""
        return {
            'event_type': event_type,
            'timestamp': time.time(),
            'random_id': random.randint(1, 10000)
        }

    def generate_events_for_timestep(self, current_time: float, event_manager: EventManager, env_info: Optional[Dict[str, Any]] = None) -> List[BaseEvent]:
        """
        为当前时间步生成事件（同步版本）
        
        Args:
            current_time: 当前时间戳
            event_manager: 事件管理器
            env_info: 通过环境信息随机生成负载
        Returns:
            List[BaseEvent]: 生成的事件列表
        """
        generated_events = []

        # 检查全局生成间隔
        if current_time - self.last_global_generation_time < self.global_generation_interval:
            return generated_events

        for event_type, config in self.event_configs.items():
            # 检查是否应该生成事件
            if not self.should_generate_event(event_type, current_time):
                continue

            # 获取事件状态
            state = self.event_states[event_type]

            # 生成事件,可能一次生成config.burst_multiplier个事件
            for _ in range(config.burst_multiplier):
                try:
                    # 生成payload
                    payload = self.generate_event_payload(event_type, env_info)

                    # 创建事件
                    event = event_manager.create_event(event_type, "trigger", payload)
                    generated_events.append(event)

                    # 更新事件状态
                    state.last_generation_time = current_time
                    state.generation_count += 1

                    # 更新成功率
                    if state.check_count > 0:
                        state.success_rate = state.generation_count / state.check_count

                    # 更新全局统计
                    self.generation_stats['total_events'] += 1
                    self.generation_stats['events_by_type'][event_type] += 1

                except Exception as e:
                    LOGGER.error(f"[EventGenerator] 生成事件失败 {event_type}: {e}")

        # 更新全局状态
        if generated_events:
            self.generation_stats['generation_times'].append(current_time)
            self.generation_stats['last_generation_time'] = current_time
            self.last_global_generation_time = current_time

        return generated_events

    def set_event_active(self, event_type: str, active: bool):
        """
        设置事件类型的激活状态
        
        Args:
            event_type: 事件类型
            active: 是否激活
        """
        if event_type in self.event_states:
            self.event_states[event_type].is_active = active
            LOGGER.info(f"[EventGenerator] 设置事件 {event_type} 激活状态: {active}")

    def set_event_cooldown(self, event_type: str, cooldown_duration: float):
        """
        设置事件类型的冷却时间
        
        Args:
            event_type: 事件类型
            cooldown_duration: 冷却时长（秒）
        """
        if event_type in self.event_states:
            self.event_states[event_type].cooldown_until = time.time() + cooldown_duration
            LOGGER.info(f"[EventGenerator] 设置事件 {event_type} 冷却时间: {cooldown_duration}秒")

    def get_event_stats(self, event_type: str = None) -> Dict[str, Any]:
        """
        获取事件生成统计信息
        
        Args:
            event_type: 指定事件类型，None表示获取全局统计
            
        Returns:
            Dict: 统计信息
        """
        if event_type:
            if event_type in self.event_states:
                state = self.event_states[event_type]
                return {
                    'event_type': event_type,
                    'generation_count': state.generation_count,
                    'burst_count': state.burst_count,
                    'last_generation_time': state.last_generation_time,
                    'is_active': state.is_active,
                    'cooldown_until': state.cooldown_until,
                    'check_count': state.check_count,
                    'consecutive_failures': state.consecutive_failures,
                    'last_check_time': state.last_check_time,
                    'success_rate': state.success_rate
                }
            return {}
        else:
            return self.generation_stats.copy()

    def reset_event_state(self, event_type: str):
        """
        重置指定事件类型的状态
        
        Args:
            event_type: 事件类型
        """
        if event_type in self.event_states:
            self.event_states[event_type] = EventGenerationState()
            LOGGER.info(f"[EventGenerator] 重置事件 {event_type} 状态")

    def reset_all_states(self):
        """重置所有事件状态"""
        for event_type in self.event_states:
            self.event_states[event_type] = EventGenerationState()
        self.generation_stats = {
            'total_events': 0,
            'events_by_type': defaultdict(int),
            'generation_times': [],
            'last_generation_time': 0.0
        }
        self.last_global_generation_time = 0.0
        LOGGER.info("[EventGenerator] 重置所有事件状态")

    def get_performance_analysis(self) -> Dict[str, Any]:
        """
        获取性能分析报告
        
        Returns:
            Dict: 性能分析数据
        """
        analysis = {
            'total_events': len(self.event_configs),
            'active_events': 0,
            'inactive_events': 0,
            'events_with_high_failure_rate': [],
            'events_with_low_success_rate': [],
            'detailed_stats': {}
        }

        for event_type, state in self.event_states.items():
            if state.is_active:
                analysis['active_events'] += 1
            else:
                analysis['inactive_events'] += 1

            # 检查高失败率事件（连续失败次数过多）
            if state.consecutive_failures > 10:
                analysis['events_with_high_failure_rate'].append({
                    'event_type': event_type,
                    'consecutive_failures': state.consecutive_failures
                })

            # 检查低成功率事件
            if state.check_count > 100 and state.success_rate < 0.01:  # 检查100次以上但成功率低于1%
                analysis['events_with_low_success_rate'].append({
                    'event_type': event_type,
                    'success_rate': state.success_rate,
                    'check_count': state.check_count
                })

            # 详细统计
            analysis['detailed_stats'][event_type] = {
                'check_count': state.check_count,
                'generation_count': state.generation_count,
                'success_rate': state.success_rate,
                'consecutive_failures': state.consecutive_failures,
                'is_active': state.is_active
            }

        return analysis
