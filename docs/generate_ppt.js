const pptxgen = require("pptxgenjs");

// Create presentation
let pres = new pptxgen();
pres.layout = 'LAYOUT_16x9';
pres.author = 'SkyEngine Team';
pres.title = '天工：仿真-调度一体化的柔性制造算法平台';
pres.subject = 'SkyEngine Platform Presentation';

// Color scheme - Teal Trust (Technical theme)
const colors = {
  primary: "028090",      // Teal
  secondary: "00A896",    // Seafoam
  accent: "02C39A",       // Mint
  dark: "1E2761",         // Navy for dark backgrounds
  light: "F8FAFC",        // Light background
  text: "1E293B",         // Dark text
  textLight: "FFFFFF",    // Light text
  border: "CBD5E1"        // Border color
};

// Helper function to add icon circle
function addIconCircle(slide, x, y, size = 0.6) {
  slide.addShape(pres.shapes.OVAL, {
    x: x, y: y, w: size, h: size,
    fill: { color: colors.accent },
    line: { color: colors.accent }
  });
}

// Slide 1: Title Slide
let slide1 = pres.addSlide();
slide1.background = { color: colors.dark };

// Title
slide1.addText("天工", {
  x: 0.5, y: 1.8, w: 9, h: 1,
  fontSize: 72, fontFace: "Arial Black", color: colors.textLight,
  align: "center", bold: true
});

// Subtitle
slide1.addText("SkyEngine: A Simulation-Scheduling Integrated FMS Platform", {
  x: 0.5, y: 2.9, w: 9, h: 0.6,
  fontSize: 20, fontFace: "Arial", color: colors.secondary,
  align: "center", italic: true
});

// Tagline
slide1.addText("仿真-调度一体化的柔性制造算法平台", {
  x: 0.5, y: 3.8, w: 9, h: 0.5,
  fontSize: 24, fontFace: "Microsoft YaHei", color: colors.textLight,
  align: "center"
});

// Decorative line
slide1.addShape(pres.shapes.LINE, {
  x: 3, y: 3.6, w: 4, h: 0,
  line: { color: colors.accent, width: 3 }
});

// Slide 2: Research Background & Motivation
let slide2 = pres.addSlide();
slide2.background = { color: colors.light };

// Title
slide2.addText("研究背景与动机", {
  x: 0.5, y: 0.3, w: 9, h: 0.7,
  fontSize: 36, fontFace: "Microsoft YaHei", color: colors.text,
  bold: true, margin: 0
});

// Subtitle
slide2.addText("Research Background & Motivation", {
  x: 0.5, y: 0.95, w: 9, h: 0.4,
  fontSize: 16, fontFace: "Arial", color: colors.secondary,
  italic: true, margin: 0
});

// Left column - Problems
slide2.addShape(pres.shapes.RECTANGLE, {
  x: 0.5, y: 1.5, w: 4.3, h: 3.8,
  fill: { color: "FFFFFF" },
  shadow: { type: "outer", color: "000000", blur: 6, offset: 2, angle: 135, opacity: 0.1 }
});

slide2.addText("传统调度系统的结构性问题", {
  x: 0.7, y: 1.7, w: 3.9, h: 0.4,
  fontSize: 16, fontFace: "Microsoft YaHei", color: colors.primary,
  bold: true, margin: 0
});

slide2.addText([
  { text: "算法与业务强耦合", options: { bullet: true, breakLine: true } },
  { text: "多目标与动态性不足", options: { bullet: true, breakLine: true } },
  { text: "仿真与真实执行割裂", options: { bullet: true, breakLine: true } },
  { text: "算法研究难以工程化", options: { bullet: true } }
], {
  x: 0.7, y: 2.2, w: 3.9, h: 2.8,
  fontSize: 13, fontFace: "Microsoft YaHei", color: colors.text,
  valign: "top"
});

// Right column - Solution
slide2.addShape(pres.shapes.RECTANGLE, {
  x: 5.2, y: 1.5, w: 4.3, h: 3.8,
  fill: { color: colors.primary },
  shadow: { type: "outer", color: "000000", blur: 6, offset: 2, angle: 135, opacity: 0.1 }
});

slide2.addText("核心思想", {
  x: 5.4, y: 1.7, w: 3.9, h: 0.4,
  fontSize: 16, fontFace: "Microsoft YaHei", color: colors.textLight,
  bold: true, margin: 0
});

slide2.addText("通过\"算法环境层 × 服务层\"两层架构，将调度算法工程化、平台化", {
  x: 5.4, y: 2.2, w: 3.9, h: 0.8,
  fontSize: 13, fontFace: "Microsoft YaHei", color: colors.textLight,
  margin: 0
});

slide2.addText("目标定位:", {
  x: 5.4, y: 3.1, w: 3.9, h: 0.3,
  fontSize: 12, fontFace: "Microsoft YaHei", color: colors.accent,
  bold: true, margin: 0
});

slide2.addText([
  { text: "高保真仿真为验证闭环", options: { bullet: true, breakLine: true } },
  { text: "从离线求解器到生产决策系统", options: { bullet: true, breakLine: true } },
  { text: "面向智能制造与数字孪生", options: { bullet: true } }
], {
  x: 5.4, y: 3.4, w: 3.9, h: 1.6,
  fontSize: 12, fontFace: "Microsoft YaHei", color: colors.textLight,
  valign: "top"
});

// Slide 3: System Architecture (Part 1)
let slide3 = pres.addSlide();
slide3.background = { color: colors.light };

slide3.addText("系统架构设计", {
  x: 0.5, y: 0.3, w: 9, h: 0.7,
  fontSize: 36, fontFace: "Microsoft YaHei", color: colors.text,
  bold: true, margin: 0
});

slide3.addText("System Architecture - Two-Layer Decoupled Design", {
  x: 0.5, y: 0.95, w: 9, h: 0.4,
  fontSize: 16, fontFace: "Arial", color: colors.secondary,
  italic: true, margin: 0
});

// Service Layer Box
slide3.addShape(pres.shapes.RECTANGLE, {
  x: 0.5, y: 1.5, w: 4.3, h: 2.2,
  fill: { color: "FFFFFF" },
  line: { color: colors.primary, width: 2 }
});

slide3.addText("服务层 (Service Layer)", {
  x: 0.7, y: 1.6, w: 3.9, h: 0.35,
  fontSize: 14, fontFace: "Microsoft YaHei", color: colors.primary,
  bold: true, margin: 0
});

slide3.addText([
  { text: "前端: Vue3 + Element Plus + ECharts", options: { bullet: true, breakLine: true } },
  { text: "后端: FastAPI (REST API + SSE)", options: { bullet: true, breakLine: true } },
  { text: "实时可视化与状态监控", options: { bullet: true } }
], {
  x: 0.7, y: 2.0, w: 3.9, h: 1.5,
  fontSize: 12, fontFace: "Microsoft YaHei", color: colors.text
});

// Algorithm Layer Box
slide3.addShape(pres.shapes.RECTANGLE, {
  x: 5.2, y: 1.5, w: 4.3, h: 2.2,
  fill: { color: colors.primary },
  line: { color: colors.primary, width: 2 }
});

slide3.addText("算法/执行器层 (Algorithm Layer)", {
  x: 5.4, y: 1.6, w: 3.9, h: 0.35,
  fontSize: 14, fontFace: "Microsoft YaHei", color: colors.textLight,
  bold: true, margin: 0
});

slide3.addText([
  { text: "调度组件: JobSolver, Assigner", options: { bullet: true, breakLine: true } },
  { text: "路径组件: A*, Greedy, MAPF-GPT", options: { bullet: true, breakLine: true } },
  { text: "仿真环境: GridFactory, PacketFactory", options: { bullet: true } }
], {
  x: 5.4, y: 2.0, w: 3.9, h: 1.5,
  fontSize: 12, fontFace: "Microsoft YaHei", color: colors.textLight
});

// Key Principles
slide3.addText("关键设计原则", {
  x: 0.5, y: 3.9, w: 9, h: 0.4,
  fontSize: 16, fontFace: "Microsoft YaHei", color: colors.text,
  bold: true, margin: 0
});

const principles = [
  { title: "服务层不关心算法实现", desc: "算法层完全独立" },
  { title: "算法层不依赖业务接口", desc: "通过稳定的接口交互" },
  { title: "环境即组件", desc: "可并行对比、快速替换" },
  { title: "仿真即验证", desc: "支持异常注入与动态扰动" }
];

principles.forEach((p, i) => {
  const xPos = 0.5 + i * 2.4;
  slide3.addShape(pres.shapes.ROUNDED_RECTANGLE, {
    x: xPos, y: 4.35, w: 2.2, h: 0.9,
    fill: { color: "FFFFFF" },
    line: { color: colors.border, width: 1 },
    rectRadius: 0.05
  });
  slide3.addText(p.title, {
    x: xPos + 0.1, y: 4.4, w: 2.0, h: 0.4,
    fontSize: 11, fontFace: "Microsoft YaHei", color: colors.primary,
    bold: true, margin: 0
  });
  slide3.addText(p.desc, {
    x: xPos + 0.1, y: 4.8, w: 2.0, h: 0.35,
    fontSize: 10, fontFace: "Microsoft YaHei", color: colors.text,
    margin: 0
  });
});

// Slide 4: System Architecture (Part 2) - FactoryProxy
let slide4 = pres.addSlide();
slide4.background = { color: colors.light };

slide4.addText("FactoryProxy 统一接口", {
  x: 0.5, y: 0.3, w: 9, h: 0.7,
  fontSize: 36, fontFace: "Microsoft YaHei", color: colors.text,
  bold: true, margin: 0
});

slide4.addText("Unified Interface for All Factory Environments", {
  x: 0.5, y: 0.95, w: 9, h: 0.4,
  fontSize: 16, fontFace: "Arial", color: colors.secondary,
  italic: true, margin: 0
});

// Lifecycle Control
slide4.addShape(pres.shapes.RECTANGLE, {
  x: 0.5, y: 1.5, w: 4.3, h: 2.0,
  fill: { color: "FFFFFF" },
  shadow: { type: "outer", color: "000000", blur: 6, offset: 2, angle: 135, opacity: 0.1 }
});

slide4.addText("生命周期控制", {
  x: 0.7, y: 1.6, w: 3.9, h: 0.35,
  fontSize: 14, fontFace: "Microsoft YaHei", color: colors.primary,
  bold: true, margin: 0
});

slide4.addText([
  { text: "initialize() - 初始化环境", options: { bullet: true, breakLine: true } },
  { text: "start() - 启动仿真", options: { bullet: true, breakLine: true } },
  { text: "pause() - 暂停仿真", options: { bullet: true, breakLine: true } },
  { text: "reset() - 重置环境", options: { bullet: true, breakLine: true } },
  { text: "stop() - 停止仿真", options: { bullet: true } }
], {
  x: 0.7, y: 2.0, w: 3.9, h: 1.4,
  fontSize: 12, fontFace: "Consolas", color: colors.text
});

// State Retrieval
slide4.addShape(pres.shapes.RECTANGLE, {
  x: 5.2, y: 1.5, w: 4.3, h: 2.0,
  fill: { color: colors.primary }
});

slide4.addText("状态获取", {
  x: 5.4, y: 1.6, w: 3.9, h: 0.35,
  fontSize: 14, fontFace: "Microsoft YaHei", color: colors.textLight,
  bold: true, margin: 0
});

slide4.addText([
  { text: "get_state_snapshot()", options: { bullet: true, breakLine: true } },
  { text: "get_metrics_snapshot()", options: { bullet: true, breakLine: true } },
  { text: "get_state_events()", options: { bullet: true, breakLine: true } }
], {
  x: 5.4, y: 2.0, w: 3.9, h: 1.4,
  fontSize: 12, fontFace: "Consolas", color: colors.textLight
});

// ProxyFactory Registration
slide4.addText("ProxyFactory 注册机制", {
  x: 0.5, y: 3.7, w: 9, h: 0.4,
  fontSize: 16, fontFace: "Microsoft YaHei", color: colors.text,
  bold: true, margin: 0
});

slide4.addShape(pres.shapes.RECTANGLE, {
  x: 0.5, y: 4.15, w: 9, h: 1.1,
  fill: { color: "F1F5F9" },
  line: { color: colors.border, width: 1 }
});

slide4.addText([
  { text: "Step 1: 实现 BaseFactoryProxy 接口", options: { breakLine: true } },
  { text: "Step 2: 使用 @ProxyFactory.register_proxy 装饰器", options: { breakLine: true } },
  { text: "Step 3: 通过 ProxyFactory.create() 动态创建代理" }
], {
  x: 0.7, y: 4.25, w: 8.6, h: 0.9,
  fontSize: 12, fontFace: "Microsoft YaHei", color: colors.text
});

// Slide 5: GridFactory Environment
let slide5 = pres.addSlide();
slide5.background = { color: colors.light };

slide5.addText("仿真环境 A: GridFactory", {
  x: 0.5, y: 0.3, w: 9, h: 0.7,
  fontSize: 36, fontFace: "Microsoft YaHei", color: colors.text,
  bold: true, margin: 0
});

slide5.addText("Grid-based Simulation for JSSP + MAPF", {
  x: 0.5, y: 0.95, w: 9, h: 0.4,
  fontSize: 16, fontFace: "Arial", color: colors.secondary,
  italic: true, margin: 0
});

// Left column - Features
slide5.addShape(pres.shapes.RECTANGLE, {
  x: 0.5, y: 1.5, w: 4.3, h: 3.5,
  fill: { color: "FFFFFF" },
  shadow: { type: "outer", color: "000000", blur: 6, offset: 2, angle: 135, opacity: 0.1 }
});

slide5.addText("核心特性", {
  x: 0.7, y: 1.6, w: 3.9, h: 0.35,
  fontSize: 14, fontFace: "Microsoft YaHei", color: colors.primary,
  bold: true, margin: 0
});

slide5.addText([
  { text: "Pogema 底层网格引擎", options: { bullet: true, breakLine: true } },
  { text: "空间均匀离散化", options: { bullet: true, breakLine: true } },
  { text: "网格步进式移动", options: { bullet: true, breakLine: true } },
  { text: "支持障碍物/机器/AGV 配置", options: { bullet: true, breakLine: true } },
  { text: "JSON 格式状态快照", options: { bullet: true } }
], {
  x: 0.7, y: 2.0, w: 3.9, h: 1.8,
  fontSize: 12, fontFace: "Microsoft YaHei", color: colors.text
});

slide5.addText("适用场景", {
  x: 0.7, y: 3.9, w: 3.9, h: 0.35,
  fontSize: 14, fontFace: "Microsoft YaHei", color: colors.primary,
  bold: true, margin: 0
});

slide5.addText([
  { text: "MAPF 路径规划研究", options: { bullet: true, breakLine: true } },
  { text: "JSSP 调度研究", options: { bullet: true, breakLine: true } },
  { text: "强化学习训练", options: { bullet: true } }
], {
  x: 0.7, y: 4.25, w: 3.9, h: 0.7,
  fontSize: 12, fontFace: "Microsoft YaHei", color: colors.text
});

// Right column - Prior Knowledge
slide5.addShape(pres.shapes.RECTANGLE, {
  x: 5.2, y: 1.5, w: 4.3, h: 3.5,
  fill: { color: colors.primary }
});

slide5.addText("先验知识", {
  x: 5.4, y: 1.6, w: 3.9, h: 0.35,
  fontSize: 14, fontFace: "Microsoft YaHei", color: colors.textLight,
  bold: true, margin: 0
});

const priorKnowledge = [
  { type: "空间先验", content: "网格尺寸、障碍物分布、边界约束" },
  { type: "机器先验", content: "网格坐标位置、加工能力" },
  { type: "任务先验", content: "工序数量、工序顺序、机器约束" },
  { type: "AGV先验", content: "初始位置、感知半径、移动能力" }
];

priorKnowledge.forEach((pk, i) => {
  const yPos = 2.0 + i * 0.75;
  slide5.addText(pk.type, {
    x: 5.4, y: yPos, w: 3.9, h: 0.25,
    fontSize: 12, fontFace: "Microsoft YaHei", color: colors.accent,
    bold: true, margin: 0
  });
  slide5.addText(pk.content, {
    x: 5.4, y: yPos + 0.25, w: 3.9, h: 0.4,
    fontSize: 11, fontFace: "Microsoft YaHei", color: colors.textLight,
    margin: 0
  });
});

// Slide 6: PacketFactory Environment
let slide6 = pres.addSlide();
slide6.background = { color: colors.light };

slide6.addText("仿真环境 B: PacketFactory", {
  x: 0.5, y: 0.3, w: 9, h: 0.7,
  fontSize: 36, fontFace: "Microsoft YaHei", color: colors.text,
  bold: true, margin: 0
});

slide6.addText("Graph-based Simulation for Real FMS", {
  x: 0.5, y: 0.95, w: 9, h: 0.4,
  fontSize: 16, fontFace: "Arial", color: colors.secondary,
  italic: true, margin: 0
});

// Left column - Features
slide6.addShape(pres.shapes.RECTANGLE, {
  x: 0.5, y: 1.5, w: 4.3, h: 2.0,
  fill: { color: "FFFFFF" },
  shadow: { type: "outer", color: "000000", blur: 6, offset: 2, angle: 135, opacity: 0.1 }
});

slide6.addText("核心特性", {
  x: 0.7, y: 1.6, w: 3.9, h: 0.35,
  fontSize: 14, fontFace: "Microsoft YaHei", color: colors.primary,
  bold: true, margin: 0
});

slide6.addText([
  { text: "拓扑图空间表示（非均匀）", options: { bullet: true, breakLine: true } },
  { text: "AGV 沿边跳转移动", options: { bullet: true, breakLine: true } },
  { text: "三文件配置体系 (YAML)", options: { bullet: true, breakLine: true } },
  { text: "完整事件驱动机制", options: { bullet: true } }
], {
  x: 0.7, y: 2.0, w: 3.9, h: 1.4,
  fontSize: 12, fontFace: "Microsoft YaHei", color: colors.text
});

// Right column - Config Files
slide6.addShape(pres.shapes.RECTANGLE, {
  x: 5.2, y: 1.5, w: 4.3, h: 2.0,
  fill: { color: colors.primary }
});

slide6.addText("配置文件体系", {
  x: 5.4, y: 1.6, w: 3.9, h: 0.35,
  fontSize: 14, fontFace: "Microsoft YaHei", color: colors.textLight,
  bold: true, margin: 0
});

slide6.addText([
  { text: "map_config.yaml - 地图布局", options: { bullet: true, breakLine: true } },
  { text: "job_config.yaml - 任务定义", options: { bullet: true, breakLine: true } },
  { text: "event_config.yaml - 事件类型", options: { bullet: true } }
], {
  x: 5.4, y: 2.0, w: 3.9, h: 1.4,
  fontSize: 12, fontFace: "Microsoft YaHei", color: colors.textLight
});

// Event Types
slide6.addText("支持的事件类型", {
  x: 0.5, y: 3.7, w: 9, h: 0.4,
  fontSize: 16, fontFace: "Microsoft YaHei", color: colors.text,
  bold: true, margin: 0
});

const eventTypes = [
  { name: "AGV_FAIL", desc: "AGV 故障" },
  { name: "MACHINE_FAIL", desc: "机器故障" },
  { name: "JOB_ADD", desc: "动态加单" },
  { name: "ENV_PAUSED", desc: "环境暂停" },
  { name: "ENV_RECOVER", desc: "环境恢复" }
];

eventTypes.forEach((et, i) => {
  const xPos = 0.5 + i * 1.9;
  slide6.addShape(pres.shapes.ROUNDED_RECTANGLE, {
    x: xPos, y: 4.15, w: 1.7, h: 1.0,
    fill: { color: "FFFFFF" },
    line: { color: colors.border, width: 1 },
    rectRadius: 0.05
  });
  slide6.addText(et.name, {
    x: xPos + 0.1, y: 4.25, w: 1.5, h: 0.4,
    fontSize: 10, fontFace: "Consolas", color: colors.primary,
    bold: true, margin: 0
  });
  slide6.addText(et.desc, {
    x: xPos + 0.1, y: 4.65, w: 1.5, h: 0.35,
    fontSize: 10, fontFace: "Microsoft YaHei", color: colors.text,
    margin: 0
  });
});

// Slide 7: Unified Interface & Extensibility
let slide7 = pres.addSlide();
slide7.background = { color: colors.light };

slide7.addText("仿真引擎与系统的交互统一性", {
  x: 0.5, y: 0.3, w: 9, h: 0.7,
  fontSize: 36, fontFace: "Microsoft YaHei", color: colors.text,
  bold: true, margin: 0
});

slide7.addText("Plug-and-Play Environment Extension", {
  x: 0.5, y: 0.95, w: 9, h: 0.4,
  fontSize: 16, fontFace: "Arial", color: colors.secondary,
  italic: true, margin: 0
});

// Core Point
slide7.addShape(pres.shapes.RECTANGLE, {
  x: 0.5, y: 1.5, w: 9, h: 0.8,
  fill: { color: colors.primary }
});

slide7.addText("核心观点：不同仿真环境通过 FactoryProxy 统一接口接入系统，实现\"即插即用\"的扩展能力", {
  x: 0.7, y: 1.65, w: 8.6, h: 0.5,
  fontSize: 14, fontFace: "Microsoft YaHei", color: colors.textLight,
  margin: 0
});

// Extension Capabilities
slide7.addText("扩展能力", {
  x: 0.5, y: 2.5, w: 9, h: 0.4,
  fontSize: 16, fontFace: "Microsoft YaHei", color: colors.text,
  bold: true, margin: 0
});

const extensions = [
  { type: "新增仿真环境", change: "仅新增 Proxy 类" },
  { type: "新增调度算法", change: "仅新增 Solver 类" },
  { type: "新增分配策略", change: "仅新增 Assigner 类" },
  { type: "新增事件类型", change: "仅新增 Event 类" }
];

extensions.forEach((ext, i) => {
  const xPos = 0.5 + i * 2.4;
  slide7.addShape(pres.shapes.ROUNDED_RECTANGLE, {
    x: xPos, y: 2.95, w: 2.2, h: 0.9,
    fill: { color: "FFFFFF" },
    line: { color: colors.border, width: 1 },
    rectRadius: 0.05
  });
  slide7.addText(ext.type, {
    x: xPos + 0.1, y: 3.0, w: 2.0, h: 0.4,
    fontSize: 11, fontFace: "Microsoft YaHei", color: colors.primary,
    bold: true, margin: 0
  });
  slide7.addText(ext.change, {
    x: xPos + 0.1, y: 3.4, w: 2.0, h: 0.35,
    fontSize: 10, fontFace: "Microsoft YaHei", color: colors.text,
    margin: 0
  });
});

// Design Advantages
slide7.addText("设计优势", {
  x: 0.5, y: 4.0, w: 4.3, h: 0.4,
  fontSize: 16, fontFace: "Microsoft YaHei", color: colors.text,
  bold: true, margin: 0
});

slide7.addText([
  { text: "服务层代码零改动", options: { bullet: true, breakLine: true } },
  { text: "前端可视化组件复用", options: { bullet: true, breakLine: true } },
  { text: "算法组件跨环境通用", options: { bullet: true } }
], {
  x: 0.5, y: 4.4, w: 4.3, h: 0.8,
  fontSize: 12, fontFace: "Microsoft YaHei", color: colors.text
});

// Environment Selection Guide
slide7.addText("环境选择指南", {
  x: 5.2, y: 4.0, w: 4.3, h: 0.4,
  fontSize: 16, fontFace: "Microsoft YaHei", color: colors.text,
  bold: true, margin: 0
});

slide7.addText([
  { text: "MAPF研究 → GridFactory", options: { bullet: true, breakLine: true } },
  { text: "柔性产线 → PacketFactory", options: { bullet: true, breakLine: true } },
  { text: "强化学习 → GridFactory", options: { bullet: true } }
], {
  x: 5.2, y: 4.4, w: 4.3, h: 0.8,
  fontSize: 12, fontFace: "Microsoft YaHei", color: colors.text
});

// Slide 8: System Demo
let slide8 = pres.addSlide();
slide8.background = { color: colors.light };

slide8.addText("实际系统演示", {
  x: 0.5, y: 0.3, w: 9, h: 0.7,
  fontSize: 36, fontFace: "Microsoft YaHei", color: colors.text,
  bold: true, margin: 0
});

slide8.addText("Live System Demonstration", {
  x: 0.5, y: 0.95, w: 9, h: 0.4,
  fontSize: 16, fontFace: "Arial", color: colors.secondary,
  italic: true, margin: 0
});

// Demo Flow
slide8.addText("演示流程", {
  x: 0.5, y: 1.5, w: 4.3, h: 0.4,
  fontSize: 16, fontFace: "Microsoft YaHei", color: colors.text,
  bold: true, margin: 0
});

const demoSteps = [
  "访问系统 (localhost:5173)",
  "选择工厂环境",
  "初始化渲染",
  "启动仿真",
  "调整速度/暂停",
  "添加任务/查看进度"
];

demoSteps.forEach((step, i) => {
  const yPos = 1.95 + i * 0.45;
  slide8.addShape(pres.shapes.OVAL, {
    x: 0.6, y: yPos + 0.05, w: 0.25, h: 0.25,
    fill: { color: colors.accent }
  });
  slide8.addText((i + 1).toString(), {
    x: 0.6, y: yPos + 0.05, w: 0.25, h: 0.25,
    fontSize: 10, fontFace: "Arial", color: colors.textLight,
    align: "center", valign: "middle", bold: true
  });
  slide8.addText(step, {
    x: 1.0, y: yPos, w: 3.8, h: 0.35,
    fontSize: 12, fontFace: "Microsoft YaHei", color: colors.text,
    margin: 0
  });
});

// Highlights
slide8.addShape(pres.shapes.RECTANGLE, {
  x: 5.2, y: 1.5, w: 4.3, h: 3.5,
  fill: { color: colors.primary }
});

slide8.addText("演示亮点", {
  x: 5.4, y: 1.6, w: 3.9, h: 0.35,
  fontSize: 14, fontFace: "Microsoft YaHei", color: colors.textLight,
  bold: true, margin: 0
});

const highlights = [
  { title: "实时性", desc: "SSE推送，毫秒级响应" },
  { title: "交互性", desc: "支持运行时暂停AGV/机器" },
  { title: "可配置性", desc: "支持上传自定义YAML" },
  { title: "可视化", desc: "实时渲染，进度清晰可见" }
];

highlights.forEach((hl, i) => {
  const yPos = 2.0 + i * 0.75;
  slide8.addText(hl.title, {
    x: 5.4, y: yPos, w: 3.9, h: 0.25,
    fontSize: 12, fontFace: "Microsoft YaHei", color: colors.accent,
    bold: true, margin: 0
  });
  slide8.addText(hl.desc, {
    x: 5.4, y: yPos + 0.25, w: 3.9, h: 0.4,
    fontSize: 11, fontFace: "Microsoft YaHei", color: colors.textLight,
    margin: 0
  });
});

// Slide 9: Summary & Future
let slide9 = pres.addSlide();
slide9.background = { color: colors.dark };

slide9.addText("总结与展望", {
  x: 0.5, y: 0.3, w: 9, h: 0.7,
  fontSize: 36, fontFace: "Microsoft YaHei", color: colors.textLight,
  bold: true, margin: 0
});

slide9.addText("Summary & Future", {
  x: 0.5, y: 0.95, w: 9, h: 0.4,
  fontSize: 16, fontFace: "Arial", color: colors.secondary,
  italic: true, margin: 0
});

// Core Values
slide9.addText("系统核心价值", {
  x: 0.5, y: 1.5, w: 4.3, h: 0.4,
  fontSize: 16, fontFace: "Microsoft YaHei", color: colors.textLight,
  bold: true, margin: 0
});

slide9.addText([
  { text: "算法工程化", options: { bullet: true, breakLine: true } },
  { text: "仿真验证闭环", options: { bullet: true, breakLine: true } },
  { text: "环境可插拔", options: { bullet: true, breakLine: true } },
  { text: "组件可替换", options: { bullet: true } }
], {
  x: 0.5, y: 1.9, w: 4.3, h: 1.4,
  fontSize: 13, fontFace: "Microsoft YaHei", color: colors.textLight
});

// Technical Highlights
slide9.addText("技术亮点", {
  x: 5.2, y: 1.5, w: 4.3, h: 0.4,
  fontSize: 16, fontFace: "Microsoft YaHei", color: colors.textLight,
  bold: true, margin: 0
});

slide9.addText([
  { text: "两层解耦架构", options: { bullet: true, breakLine: true } },
  { text: "FactoryProxy 统一接口", options: { bullet: true, breakLine: true } },
  { text: "Coordinator 三层决策", options: { bullet: true, breakLine: true } },
  { text: "多环境支持", options: { bullet: true, breakLine: true } },
  { text: "事件驱动机制", options: { bullet: true } }
], {
  x: 5.2, y: 1.9, w: 4.3, h: 1.6,
  fontSize: 13, fontFace: "Microsoft YaHei", color: colors.textLight
});

// Project Info
slide9.addShape(pres.shapes.RECTANGLE, {
  x: 0.5, y: 3.7, w: 9, h: 1.3,
  fill: { color: colors.primary }
});

slide9.addText("项目信息", {
  x: 0.7, y: 3.8, w: 8.6, h: 0.35,
  fontSize: 14, fontFace: "Microsoft YaHei", color: colors.textLight,
  bold: true, margin: 0
});

slide9.addText([
  { text: "项目名称: SkyEngine（天工）  |  许可证: Apache 2.0", options: { breakLine: true } },
  { text: "GitHub: https://github.com/dayu-autostreamer/skyengine", options: { breakLine: true } },
  { text: "联系方式: lxie@nju.edu.cn | wuhao@smail.nju.edu.cn" }
], {
  x: 0.7, y: 4.2, w: 8.6, h: 0.7,
  fontSize: 12, fontFace: "Microsoft YaHei", color: colors.textLight
});

// Save presentation
pres.writeFile({ fileName: "E:\\Project\\GroupWork\\skyengine\\docs\\天工平台演示.pptx" })
  .then(() => {
    console.log("PPT generated successfully: 天工平台演示.pptx");
  })
  .catch(err => {
    console.error("Error generating PPT:", err);
  });
