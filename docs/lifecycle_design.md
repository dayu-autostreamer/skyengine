参考SpringBoot的生命周期设计,对sky_simulator整体进行类似的设计.

---
🌱 1. 启动引导阶段（Bootstrap）

引用对应的 environment_env.py后,
创建 `环境` 实例，确定当前是 `仿真` 环境 还是 `实机` 环境。 

[//]: # (加载并调用 Initializer,用于初始化环境上下文。)

---

⚙️ 2. 环境准备阶段（Environment Preparation）

创建 Environment（如 packet_factory_env 或 stream_factory_env）。
此时需要加载全局的配置文件（如 application.yml）。
加载并调用 PostProcessor, 在该回调中进行后处理。

---
🏗 3. 上下文创建阶段（Context Creation）

创建 `组件`,如果是仿真环境,直接创建对应的类;如果是实际环境,尝试建立连接确保组件存活。
注册 `组件`,如基础AGV/Machine等
加载并调用 ContextCreator 的实现类。

---
🔧 4. 组件自身加载阶段（Component Definition Load）

扫描并注册配置类、组件。
执行自动配置。

---
🏁 5. 环境交互阶段（Environment Ready）

此时开始环境的执行.

