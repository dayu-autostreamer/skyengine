# 生命周期设计

参考SpringBoot的生命周期设计,对tiangong_simulator整体进行类似的设计.
使用了 "组件注册表 + 动态工厂 + 环境标识" 机制实现从文件中动态创建.
---
🌱 1. 启动引导阶段（Initialize Bootstrap）

引用对应的 environment_env.py后,
 - 读取全局的配置文件（即 application.yml）,检查配置文件中指定的其他文件是否存在. 
 - 扫描环境中的类组件 标注唯一的ID与其对应, 后续通过ID索引+反射创建对象.

---

⚙️ 2. 环境准备阶段（Environment Preparation）

 - 创建 Environment（如 packet_factory_env 或 stream_factory_env）.
 - 创建指定策略的Agent, 并将其与环境进行组装.
对于组件, 以agent为例, 其寻址方式为env_name.agent_name.

---
🏗 3. 上下文创建阶段（Context Creation）

测试活性
创建 `组件`,如果是仿真环境,直接创建对应的类;如果是实际环境,尝试建立连接确保组件存活.
注册 `组件`,如基础AGV/Machine等.

---
🏁 4. 环境交互阶段（Environment Ready）

此时开始环境的执行.

---
```
🔧 额外阶段: 组件自身的加载阶段（Component Definition Load）

initialize() ──► [connect()]  ──► start()
      │                            │             
      ▼                            ▼            
    stop() <─────────────────── update()

每个组件本身的生命周期:
 - 初始化 initialize()
 - 连接 connect()
 - 启动 start()
 - 更新 update()
 - 终止 stop()
```

