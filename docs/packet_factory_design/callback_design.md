# 回调函数族设计

---
🌱 1. 环境构建类

load_graph 加载环境图结构（AGV/Machine/Job）

---

⚙️ 2. 智能体相关

before_decision	step开始前动作决策前注入特征或状态修饰

after_decision step后决策完成后修正或分析决策

---
🏗 3. 运行监控与分析类

initialize_visualizer 初始化可视化器（Matplotlib / Pygame）

detect_deadlock 检查AGV或任务死锁状态

---
🏁 4. 执行调度阶段

before_step 每轮 env_step 前	自定义行为前钩子（如状态记录）

after_step	每轮 env_step 后	自定义行为后钩子（如时间同步）


---


