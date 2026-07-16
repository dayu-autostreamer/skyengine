import { defineStore } from "pinia";
import { ref, computed, nextTick } from "vue";
import { ZONE_COLORS } from "@/utils/assets";
import { apiGet, API_ROUTES } from "@/utils/api";

// ─────────────────────────────────────────────
// 常量
// ─────────────────────────────────────────────

/** 将 Three.js 十六进制颜色转为 CSS rgba 字符串 */
function hexToRgba(hex, alpha = 0.15) {
  const r = (hex >> 16) & 0xff;
  const g = (hex >> 8) & 0xff;
  const b = hex & 0xff;
  return `rgba(${r},${g},${b},${alpha})`;
}
const STORAGE_KEYS = {
  SELECTED_FACTORY: "selectedFactoryId",
};

const DEFAULT_RENDER_CONFIG = Object.freeze({
  baseGridSize: 40,
  gridWidth: 20,
  gridHeight: 14,
  colors: {},
});

// ─────────────────────────────────────────────
// 资产模板注册表
// ─────────────────────────────────────────────
export const ASSET_TEMPLATES = Object.freeze({
  zone_restricted: {
    type: 'zone',
    icon: '🔒',
    name: '禁区',
    template: { type: 'restricted', area: { x: 0, y: 0, w: 2, h: 2 }, color: hexToRgba(ZONE_COLORS.restricted) },
  },
  zone_workbench: {
    type: 'zone',
    icon: '🔧',
    name: '工位',
    template: { type: 'workbench', area: { x: 0, y: 0, w: 1, h: 1 }, color: hexToRgba(ZONE_COLORS.workbench) },
  },
  zone_obstacle: {
    type: 'zone',
    icon: '🚫',
    name: '障碍物',
    template: { type: 'obstacle', area: { x: 0, y: 0, w: 1, h: 1 }, color: hexToRgba(ZONE_COLORS.obstacle) },
  },
  zone_workarea: {
    type: 'zone',
    icon: '📦',
    name: '工作区',
    template: { type: 'workarea', area: { x: 0, y: 0, w: 3, h: 2 }, color: hexToRgba(ZONE_COLORS.workarea) },
  },
  machine: {
    type: 'machine',
    icon: '⚙️',
    name: '加工机器',
    template: { size: [2, 2], status: 'IDLE' },
  },
  waypoint_dock: {
    type: 'waypoint',
    icon: '🚪',
    name: '停靠点',
    template: { type: 'dock' },
  },
  waypoint_route: {
    type: 'waypoint',
    icon: '📍',
    name: '路由点',
    template: { type: 'route' },
  },
  agv: {
    type: 'agv',
    icon: '🤖',
    name: 'AGV',
    template: { velocity: 1.0, capacity: 100, status: 'IDLE' },
  },
  // ── 装饰资产（统一编码为 obstacle 区域） ──
  decor_bollard: {
    type: 'zone',
    icon: '🔶',
    name: '警示柱',
    template: { type: 'obstacle', decor: 'bollard', area: { x: 0, y: 0, w: 1, h: 1 }, color: hexToRgba(ZONE_COLORS.obstacle) },
  },
  decor_rack: {
    type: 'zone',
    icon: '🗄️',
    name: '储物架',
    template: { type: 'obstacle', decor: 'rack', area: { x: 0, y: 0, w: 1, h: 1 }, color: hexToRgba(ZONE_COLORS.obstacle) },
  },
  decor_cabinet: {
    type: 'zone',
    icon: '🔌',
    name: '配电箱',
    template: { type: 'obstacle', decor: 'cabinet', area: { x: 0, y: 0, w: 1, h: 1 }, color: hexToRgba(ZONE_COLORS.obstacle) },
  },
  decor_barrier: {
    type: 'zone',
    icon: '🚧',
    name: '安全隔离栏',
    template: { type: 'obstacle', decor: 'barrier', area: { x: 0, y: 0, w: 3, h: 1 }, color: hexToRgba(ZONE_COLORS.obstacle) },
  },
});

const EMPTY_GRID_STATE = Object.freeze({
  env_timeline: "0",
  grid_state: { positions_xy: [], is_active: [], agv_status: [], agv_repair_remaining: [] },
  machines: {},
  event_epoch: 0,
  map_epoch: 0,
  machine_epoch: 0,
  agv_epoch: 0,
  job_epoch: 0,
  event_metrics: {},
  events: [],
  blocked_cells: [],
  active_transfers: [],
});

// ─────────────────────────────────────────────
// 工具函数
// ─────────────────────────────────────────────

/**
 * 构建工厂静态资源 URL。
 * 使用 import.meta.url 确保 Vite 生产构建后路径依然有效。
 */
function getAssetUrl(name) {
  if (!name) return "";
  return new URL(`../assets/factories/${name}`, import.meta.url).href;
}

/**
 * 校验配置对象的必要字段，通过返回 true。
 */
function validateConfig(config) {
  if (!config || typeof config !== "object") return false;
  if (typeof config.id !== "string" || !config.id.trim()) return false;
  return true;
}

/**
 * 规范化快照，填充缺失字段，保证后续消费安全。
 *
 * machines 归一化:
 * - DockerFactory (sim_server) 输出 list[{id:int,...}] → 转 dict keyed by "M{id}"
 * - StaticFactory 输出 dict{"M1":{...}} → 保持
 * - 保留所有原字段 (status / current_op / queue_length / load 等)
 *
 * jobs 字段透传 (DockerFactory 才有):
 * - list[{job_id, ops:[...], progress:{done,total}, ...}] → 原样保留
 * - 缺失时给空 list, 下游消费安全
 */
function normalizeSnapshot(snapshot, fallbackIndex) {
  const rawMachines = snapshot.machines ?? {}
  let machinesDict
  if (Array.isArray(rawMachines)) {
    // list → dict keyed by "M{id}"
    machinesDict = {}
    rawMachines.forEach((m) => {
      const key = `M${m.id}`
      machinesDict[key] = m
    })
  } else {
    machinesDict = rawMachines
  }

  return {
    env_timeline:
      snapshot.timestamp ?? snapshot.env_timeline ?? `T+${fallbackIndex}`,
    timestamp: snapshot.timestamp ?? null,
    grid_state: snapshot.grid_state ?? { positions_xy: [], is_active: [], agv_status: [], agv_repair_remaining: [] },
    event_epoch: snapshot.event_epoch ?? 0,
    map_epoch: snapshot.map_epoch ?? 0,
    machine_epoch: snapshot.machine_epoch ?? 0,
    agv_epoch: snapshot.agv_epoch ?? 0,
    job_epoch: snapshot.job_epoch ?? 0,
    event_metrics: snapshot.event_metrics ?? {},
    events: Array.isArray(snapshot.events) ? snapshot.events : [],
    blocked_cells: Array.isArray(snapshot.blocked_cells) ? snapshot.blocked_cells : [],
    machines: machinesDict,
    jobs: Array.isArray(snapshot.jobs) ? snapshot.jobs : [],
    active_transfers: snapshot.active_transfers ?? [],
    insertion_requests: Array.isArray(snapshot.insertion_requests) ? snapshot.insertion_requests : [],
  }
}

// ─────────────────────────────────────────────
// Store 定义
// ─────────────────────────────────────────────
export const useFactoryStore = defineStore("factory", () => {
  // ══════════════════════════════════════════
  // 1. 工厂列表
  // ══════════════════════════════════════════
  const factories = ref([
    {
      id: "packet_factory",
      name: "翼辉电池装配无人产线",
      image: getAssetUrl("packet_factory.jpg"),
      description:
        "地处华东核心制造区，配备智能 AGV 运输与全自动机器人电池装配流水线。",
    },
    {
      id: "grid_factory",
      name: "翼辉原料分拣仓",
      image: getAssetUrl("grid_factory.jpg"),
      description:
        "坐落于华东关键物流节点，拥有 AGV 智能分拣与自动化货物存储管理系统。",
    },
    {
      id: "northeast_center",
      name: "北满钢铁制造中心",
      image:
        "https://images.unsplash.com/photo-1581091226825-a6a2a5aee158?q=80&w=1000&auto=format&fit=crop",
      description: "位于东北地区的原材料制造基地，拥有成熟的钢材生产线。",
    },
    {
      id: "southwest_logistics",
      name: "西南铝业制造中心",
      image:
        "https://images.unsplash.com/photo-1454165804606-c3d57bc86b40?q=80&w=1000&auto=format&fit=crop",
      description: "地处西南核心制造区，拥有先进的铝材生产线。",
    },
    {
      id: "grid_factory_new",
      name: "翼辉原料分拣仓 (容器化)",
      image: getAssetUrl("grid_factory.jpg"),
      description:
        "Docker 容器化仿真引擎，算法按需启动，支持动态调度。",
    },
  ]);

  const selectedFactoryId = ref(
    localStorage.getItem(STORAGE_KEYS.SELECTED_FACTORY) ?? "packet_factory",
  );

  const currentFactory = computed(() =>
    factories.value.find((f) => f.id === selectedFactoryId.value) ?? null,
  );

  function getFactories() {
    return factories.value;
  }

  function setCurrentFactory(factoryId) {
    const exists = factories.value.some((f) => f.id === factoryId);
    if (!exists) {
      console.warn(`[FactoryStore] 未知工厂 ID: ${factoryId}`);
      return;
    }
    selectedFactoryId.value = factoryId;
    localStorage.setItem(STORAGE_KEYS.SELECTED_FACTORY, factoryId);
  }

  // ══════════════════════════════════════════
  // 2. 工厂配置管理
  // ══════════════════════════════════════════

  /**
   * 配置持久化到 localStorage，刷新后可恢复完整内容。
   * 读取时做 validateConfig 二次校验，防止缓存数据损坏导致崩溃。
   */
  const factoryConfigs = ref({});

  const currentConfigId = ref(null);
  const runtimeExceptionConfig = ref(null);
  const runtimeProcessingTimeConfig = ref(null);

  /** 3D 重建提示：记录最近一次编辑操作的资产类型，供 watch 精准局部重建 */
  const rebuildHint = ref(null);   // 'zone' | 'machine' | 'waypoint' | 'agv' | null

  const currentConfig = computed(() => {
    if (!currentConfigId.value) return null;
    return factoryConfigs.value[currentConfigId.value] ?? null;
  });

  const currentTopologyConfig = computed(
    () => currentConfig.value?.topology ?? null,
  );

  const currentRenderConfig = computed(
    () => currentConfig.value?.renderConfig ?? { ...DEFAULT_RENDER_CONFIG },
  );

  /**
   * 加载并激活一个外部配置文件对象。
   * 会先做字段校验，失败时抛出错误而非静默写入。
   */
  function loadConfigFromFile(config) {
    if (!validateConfig(config)) {
      throw new Error(
        "[FactoryStore] loadConfigFromFile: 无效配置，缺少 id 字段。",
      );
    }
    factoryConfigs.value[config.id] = config;
    currentConfigId.value = config.id;
    setRuntimeProfiles({
      exceptionConfig: config.exception_config ?? null,
      processingTimeConfig: config.processing_time_config ?? null,
    });
  }

  function setRuntimeProfiles({ exceptionConfig = null, processingTimeConfig = null } = {}) {
    runtimeExceptionConfig.value = exceptionConfig
      ? JSON.parse(JSON.stringify(exceptionConfig))
      : null;
    runtimeProcessingTimeConfig.value = processingTimeConfig
      ? JSON.parse(JSON.stringify(processingTimeConfig))
      : null;
  }

  function setCurrentConfig(configId) {
    if (!factoryConfigs.value[configId]) {
      console.warn(`[FactoryStore] 未找到配置 ID: ${configId}`);
      return;
    }
    currentConfigId.value = configId;
  }

  function getLoadedConfigs() {
    return Object.values(factoryConfigs.value);
  }

  function deleteConfig(configId) {
    delete factoryConfigs.value[configId];
    if (currentConfigId.value === configId) {
      currentConfigId.value = null;
    }
  }

  /**
   * 从拓扑数据对象直接构建完整配置并激活。
   * @returns {string} 生成的配置 ID
   */
  function setCurrentTopologyConfig(topologyData) {
    const configId =
      typeof topologyData.id === "string" && topologyData.id.trim()
        ? topologyData.id
        : `temp_config_${Date.now()}`;

    const completeConfig = {
      id: configId,
      name: topologyData.name ?? "临时配置",
      version: topologyData.version ?? "1.0",
      timestamp: Date.now(),
      topology: {
        zones: topologyData.zones ?? [],
        machines: topologyData.machines ?? {},
        waypoints: topologyData.waypoints ?? {},
        gridWidth: topologyData.gridWidth ?? DEFAULT_RENDER_CONFIG.gridWidth,
        gridHeight: topologyData.gridHeight ?? DEFAULT_RENDER_CONFIG.gridHeight,
      },
      agvs: (topologyData.agvs ?? []).map((agv) => ({
        id: agv.id,
        name: agv.name ?? `AGV-${agv.id}`,
        initialLocation: agv.initialLocation ?? [0, 0],
        velocity: agv.velocity ?? 1.0,
        capacity: agv.capacity ?? 100,
        status: agv.status ?? "IDLE",
      })),
      renderConfig: {
        baseGridSize:
          topologyData.baseGridSize ?? DEFAULT_RENDER_CONFIG.baseGridSize,
        gridWidth: topologyData.gridWidth ?? DEFAULT_RENDER_CONFIG.gridWidth,
        gridHeight: topologyData.gridHeight ?? DEFAULT_RENDER_CONFIG.gridHeight,
        colors: topologyData.colors ?? {},
      },
    };

    factoryConfigs.value[configId] = completeConfig;
    currentConfigId.value = configId;

    return configId;
  }

  // ──────────────────────────────────────────
  // 配置辅助查询
  // ──────────────────────────────────────────

  function getAGVs() {
    return currentConfig.value?.agvs ?? [];
  }

  function getCurrentAssets() {
    return (
      currentConfig.value?.topology ?? {
        zones: [],
        machines: {},
        waypoints: {},
      }
    );
  }

  // 配置中的静态任务实例（job_list）。当未启动仿真、currentState.jobs 为空时，
  // UI 仍可基于此展示 Job 列表（与 machines 同样降级到配置）。
  // 结构：{ job_id, name?, operations:[{machine_id, duration, name?}],
  //         arrival_time, due_time, priority? }
  function getJobs() {
    return currentConfig.value?.jobs?.job_list ?? [];
  }
  // machine_id(int) → machine key(string) 映射，便于把工序的 machine_id 翻成 "MACHINE_1_1"
  function getJobMachineIdMap() {
    return currentConfig.value?.jobs?._machine_id_map ?? {};
  }

  function getMachineRuntimeKey(machineRef, state = null) {
    if (machineRef == null) return null;
    const source = state ?? latestState.value;
    const stateMachines = source?.machines ?? {};
    const refValue = String(machineRef);

    if (Object.prototype.hasOwnProperty.call(stateMachines, refValue)) return refValue;

    const stateEntry = Object.entries(stateMachines).find(([, machine]) =>
      [machine?.id, machine?.runtime_id, machine?.config_key, machine?.config_id]
        .some((value) => value != null && String(value) === refValue),
    );
    if (stateEntry) return stateEntry[0];

    const runtimeMatch = refValue.match(/^M?(\d+)$/i);
    if (runtimeMatch) return `M${runtimeMatch[1]}`;

    const configMachines = currentConfig.value?.topology?.machines ?? {};
    const configEntry = Object.entries(configMachines).find(([configKey, machine]) =>
      configKey === refValue || String(machine?.id) === refValue,
    );
    if (!configEntry) return refValue;

    const [configKey] = configEntry;
    const runtimeMapEntry = Object.entries(getJobMachineIdMap())
      .find(([, mappedConfigKey]) => mappedConfigKey === configKey);
    if (runtimeMapEntry) return `M${runtimeMapEntry[0]}`;

    const configIndex = Object.keys(configMachines).indexOf(configKey);
    return Object.keys(stateMachines)[configIndex] ?? refValue;
  }

  function getMachineConfig(machineRef, state = null) {
    if (machineRef == null) return null;
    const configMachines = currentConfig.value?.topology?.machines ?? {};
    const refValue = String(machineRef);
    const directEntry = Object.entries(configMachines).find(([configKey, machine]) =>
      configKey === refValue || String(machine?.id) === refValue,
    );
    if (directEntry) return directEntry[1];

    const runtimeKey = getMachineRuntimeKey(machineRef, state);
    const runtimeId = String(runtimeKey).match(/^M(\d+)$/i)?.[1];
    if (runtimeId == null) return null;
    const configKey = getJobMachineIdMap()[runtimeId];
    return configMachines[configKey] ?? null;
  }

  function getMachineDisplayName(machineRef, state = null) {
    if (machineRef == null) return "—";
    const source = state ?? latestState.value;
    const runtimeKey = getMachineRuntimeKey(machineRef, source);
    const machine = source?.machines?.[runtimeKey];
    const runtimeName = machine?.display_name ?? machine?.name;
    if (runtimeName) return runtimeName;

    const configMachine = getMachineConfig(machineRef, source);
    return configMachine?.name ?? configMachine?.id ?? runtimeKey;
  }

  function getAssetsStats() {
    const { zones = [], machines = {}, waypoints = {} } = getCurrentAssets();
    const agvCount = getAGVs().length;
    const zoneCount = zones.length;
    const machineCount = Object.keys(machines).length;
    const waypointCount = Object.keys(waypoints).length;
    return {
      zoneCount,
      machineCount,
      waypointCount,
      agvCount,
      totalAssets: zoneCount + machineCount + waypointCount + agvCount,
    };
  }

  function formatAssetsList() {
    const { zones = [], machines = {}, waypoints = {} } = getCurrentAssets();
    const agvs = getAGVs();
    const list = [];

    const ZONE_ICON_MAP = {
      restricted: '🔒',
      workbench: '🔧',
      obstacle: '🚫',
      workarea: '📦',
    };
    const DECOR_ICON_MAP = {
      bollard: '🔶',
      rack: '🗄️',
      cabinet: '🔌',
      barrier: '🚧',
    };

    zones.forEach((zone) => {
      const isDecor = !!zone.decor;
      list.push({
        type: "zone",
        icon: isDecor ? (DECOR_ICON_MAP[zone.decor] ?? '🚫') : (ZONE_ICON_MAP[zone.type] ?? '🔒'),
        name: zone.name ?? `Zone ${zone.id}`,
        description: isDecor ? `装饰物: ${zone.decor}` : `区域类型: ${zone.type ?? "unknown"}`,
        data: zone,
      });
    });

    Object.entries(machines).forEach(([key, machine]) => {
      list.push({
        type: "machine",
        icon: "⚙️",
        name: machine.name ?? `Machine ${key}`,
        description: `状态: ${machine.status ?? "UNKNOWN"}`,
        data: machine,
      });
    });

    Object.entries(waypoints).forEach(([key, waypoint]) => {
      list.push({
        type: "waypoint",
        icon: waypoint.type === "dock" ? "🚪" : "📍",
        name: waypoint.name ?? `Waypoint ${key}`,
        description: `类型: ${waypoint.type ?? "route"}`,
        data: waypoint,
      });
    });

    agvs.forEach((agv) => {
      list.push({
        type: "agv",
        icon: "🤖",
        name: agv.name ?? `AGV-${agv.id}`,
        description: `速度: ${agv.velocity ?? 1.0}, 容量: ${agv.capacity ?? 100}`,
        data: agv,
      });
    });

    return list;
  }

  // ──────────────────────────────────────────
  // 资产编辑 CRUD
  // ──────────────────────────────────────────

  /**
   * 获取所有已占用的网格坐标集合。
   * 返回 Set<string>，key 格式 "gx,gy"。
   */
  function getOccupiedCells(excludeAssetId = null, excludeAssetType = null) {
    const cfg = currentConfig.value;
    if (!cfg) return new Set();
    const topo = cfg.topology;
    const occupied = new Set();

    // 机器占用 location 所在格（按 m.id 字段匹配，避免字典 key 与 m.id 不一致）
    Object.values(topo.machines || {}).forEach((m) => {
      if (excludeAssetType === 'machine' && m.id === excludeAssetId) return;
      if (m.location) {
        const [x, y] = m.location;
        const sw = m.size?.[0] || 1;
        const sh = m.size?.[1] || 1;
        for (let dx = 0; dx < sw; dx++) {
          for (let dy = 0; dy < sh; dy++) {
            occupied.add(`${x + dx},${y + dy}`);
          }
        }
      }
    });

    // 路由点占 1 格
    Object.entries(topo.waypoints || {}).forEach(([key, wp]) => {
      if (excludeAssetType === 'waypoint' && key === excludeAssetId) return;
      if (wp.location) occupied.add(`${wp.location[0]},${wp.location[1]}`);
    });

    // 区域占 area 范围
    (topo.zones || []).forEach((z) => {
      if (excludeAssetType === 'zone' && z.id === excludeAssetId) return;
      if (z.area) {
        const { x, y, w, h } = z.area;
        for (let dx = 0; dx < (w || 1); dx++) {
          for (let dy = 0; dy < (h || 1); dy++) {
            occupied.add(`${x + dx},${y + dy}`);
          }
        }
      }
    });

    // AGV 占 initialLocation 所在格
    (cfg.agvs || []).forEach((agv) => {
      if (excludeAssetType === 'agv' && String(agv.id) === String(excludeAssetId)) return;
      if (agv.initialLocation) occupied.add(`${agv.initialLocation[0]},${agv.initialLocation[1]}`);
    });

    return occupied;
  }

  /**
   * 从中心开始螺旋扫描，找到第一个空闲位置。
   */
  function findFreeCell(occupied, gridW, gridH) {
    const cx = Math.floor(gridW / 2);
    const cy = Math.floor(gridH / 2);
    // 螺旋搜索
    for (let r = 0; r < Math.max(gridW, gridH); r++) {
      for (let dx = -r; dx <= r; dx++) {
        for (let dy = -r; dy <= r; dy++) {
          if (Math.abs(dx) !== r && Math.abs(dy) !== r) continue; // 只检查边界
          const gx = cx + dx;
          const gy = cy + dy;
          if (gx < 0 || gx >= gridW || gy < 0 || gy >= gridH) continue;
          if (!occupied.has(`${gx},${gy}`)) return [gx, gy];
        }
      }
    }
    return [cx, cy]; // fallback
  }

  /**
   * 从模板添加资产到当前配置，返回新资产名称。
   * 自动寻找空闲网格位置。
   */
  function addAssetFromTemplate(templateId) {
    const tpl = ASSET_TEMPLATES[templateId];
    if (!tpl) throw new Error(`未知模板: ${templateId}`);
    const cfg = currentConfig.value;
    if (!cfg) throw new Error('请先加载或创建配置');

    // 设置重建提示，让 3D 组件只重建受影响的组
    rebuildHint.value = tpl.type;

    const topo = cfg.topology;
    const gw = topo.gridWidth || 20;
    const gh = topo.gridHeight || 14;
    const id = `${tpl.type}_${Date.now()}`;
    const defaultName = `${tpl.name}_${Object.keys(
      tpl.type === 'zone' ? (topo.zones || []) :
      tpl.type === 'machine' ? (topo.machines || {}) :
      (topo.waypoints || {})
    ).length + 1}`;

    const occupied = getOccupiedCells();
    const [freeX, freeY] = findFreeCell(occupied, gw, gh);

    if (tpl.type === 'zone') {
      if (!topo.zones) topo.zones = [];
      const area = { ...(tpl.template.area || { x: 0, y: 0, w: 1, h: 1 }) };
      area.x = freeX;
      area.y = freeY;
      topo.zones.push({ id, name: defaultName, ...tpl.template, area });
    } else if (tpl.type === 'machine') {
      if (!topo.machines) topo.machines = {};
      topo.machines[id] = { id, name: defaultName, location: [freeX, freeY], ...tpl.template };
    } else if (tpl.type === 'waypoint') {
      if (!topo.waypoints) topo.waypoints = {};
      topo.waypoints[id] = { location: [freeX, freeY], ...tpl.template, name: defaultName, id };
    } else if (tpl.type === 'agv') {
      if (!cfg.agvs) cfg.agvs = [];
      const agvId = cfg.agvs.length;
      cfg.agvs.push({
        id: agvId,
        name: defaultName,
        initialLocation: [freeX, freeY],
        ...tpl.template,
      });
    }

    // rebuildHint 由 3D 组件的 deep watcher 负责清除，
    // 避免 nextTick 时序竞争导致 watcher 读到 null 而触发全量重建。
    return defaultName;
  }

  /**
   * 检查目标位置是否被其他资产占用。
   */
  function isCellOccupied(gridX, gridY, excludeAssetId = null, excludeAssetType = null) {
    const occupied = getOccupiedCells(excludeAssetId, excludeAssetType);
    return occupied.has(`${gridX},${gridY}`);
  }

  /**
   * 更新资产网格位置（带碰撞校验）。
   * 返回 true 表示移动成功，false 表示位置被占用。
   */
  function updateAssetPosition(assetType, assetId, gridX, gridY) {
    const cfg = currentConfig.value;
    if (!cfg) return false;
    const topo = cfg.topology;

    // 碰撞校验：排除自身
    if (isCellOccupied(gridX, gridY, assetId, assetType)) return false;

    if (assetType === 'machine' && topo.machines) {
      // 按 m.id 字段查找（字典 key 可能与 m.id 不一致）
      const machine = Object.values(topo.machines).find(m => m.id === assetId);
      if (!machine) return false;
      machine.location = [gridX, gridY];
    } else if (assetType === 'waypoint' && topo.waypoints) {
      const wp = Object.values(topo.waypoints).find(w => w.id === assetId);
      if (!wp) return false;
      wp.location = [gridX, gridY];
    } else if (assetType === 'zone' && topo.zones) {
      const zone = topo.zones.find(z => z.id === assetId);
      if (!zone || !zone.area) return false;
      zone.area.x = gridX;
      zone.area.y = gridY;
    } else if (assetType === 'agv' && cfg.agvs) {
      const agv = cfg.agvs.find(a => String(a.id) === String(assetId));
      if (!agv) return false;
      agv.initialLocation = [gridX, gridY];
    } else {
      return false;
    }
    return true;
  }

  /**
   * 重命名资产。
   */
  function renameAsset(assetType, assetId, newName) {
    const cfg = currentConfig.value;
    if (!cfg) return;
    const topo = cfg.topology;

    if (assetType === 'machine' && topo.machines) {
      const machine = Object.values(topo.machines).find(m => m.id === assetId);
      if (machine) machine.name = newName;
    } else if (assetType === 'waypoint' && topo.waypoints) {
      const wp = Object.values(topo.waypoints).find(w => w.id === assetId);
      if (wp) wp.name = newName;
    } else if (assetType === 'zone' && topo.zones) {
      const zone = topo.zones.find(z => z.id === assetId);
      if (zone) zone.name = newName;
    } else if (assetType === 'agv' && cfg.agvs) {
      const agv = cfg.agvs.find(a => String(a.id) === String(assetId));
      if (agv) agv.name = newName;
    }
  }

  /**
   * 删除资产。
   */
  function removeAsset(assetType, assetId) {
    const cfg = currentConfig.value;
    if (!cfg) return;
    const topo = cfg.topology;

    rebuildHint.value = assetType;

    if (assetType === 'machine' && topo.machines) {
      const dictKey = Object.keys(topo.machines).find(k => topo.machines[k].id === assetId);
      if (dictKey) delete topo.machines[dictKey];
    } else if (assetType === 'waypoint' && topo.waypoints) {
      const dictKey = Object.keys(topo.waypoints).find(k => topo.waypoints[k].id === assetId);
      if (dictKey) delete topo.waypoints[dictKey];
    } else if (assetType === 'zone' && topo.zones) {
      topo.zones = topo.zones.filter(z => z.id !== assetId);
    } else if (assetType === 'agv' && cfg.agvs) {
      cfg.agvs = cfg.agvs.filter(a => String(a.id) !== String(assetId));
    }
    // rebuildHint 由 3D 组件的 deep watcher 负责清除。
  }

  /**
   * 导出当前配置的深拷贝（用于下载）。
   */
  function exportCurrentConfig() {
    if (!currentConfig.value) return null;
    return JSON.parse(JSON.stringify(currentConfig.value));
  }

  // ══════════════════════════════════════════
  // 3. 动画状态
  // ══════════════════════════════════════════

  const historyBuffer = ref([]);
  const commandQueue = ref([]);
  const currentIndex = ref(0);
  const isPlaying = ref(false);
  const playbackSpeed = ref(1000);

  /**
   * 是否处于"跟随直播尾部"模式。
   * 用户手动拖动进度条后自动关闭，新帧推入时如果处于此模式则自动跟进。
   */
  const isLiveMode = ref(true);

  const totalSteps = computed(() => historyBuffer.value.length);

  const currentState = computed(() => {
    if (historyBuffer.value.length === 0) return { ...EMPTY_GRID_STATE };
    const idx = Math.min(
      Math.max(0, currentIndex.value),
      historyBuffer.value.length - 1,
    );
    return historyBuffer.value[idx];
  });

  const latestState = computed(() => {
    if (historyBuffer.value.length === 0) return { ...EMPTY_GRID_STATE };
    return historyBuffer.value[historyBuffer.value.length - 1];
  });

  // ──────────────────────────────────────────
  // 动画动作
  // ──────────────────────────────────────────

  // 模块① machine ↔ Job 双向联动选中态
  const selectedMachineKey = ref(null) // 形如 "M3"
  const selectedJobId = ref(null) // 数字 job_id
  const selectedAgvIndex = ref(null) // AGV 在 positions_xy 中的下标

  function selectMachine(key) {
    const runtimeKey = getMachineRuntimeKey(key, currentState.value)
    const next = selectedMachineKey.value === runtimeKey ? null : runtimeKey
    selectedMachineKey.value = next
    if (next != null) {
      selectedJobId.value = null
      selectedAgvIndex.value = null
    }
  }
  function selectJob(jobId) {
    const next = selectedJobId.value === jobId ? null : jobId
    selectedJobId.value = next
    if (next != null) {
      selectedMachineKey.value = null
      selectedAgvIndex.value = null
    }
  }
  function selectAgv(index) {
    const next = selectedAgvIndex.value === index ? null : index
    selectedAgvIndex.value = next
    if (next != null) {
      selectedMachineKey.value = null
      selectedJobId.value = null
    }
  }

  function reset() {
    isPlaying.value = false;
    currentIndex.value = 0;
    historyBuffer.value = [];
    commandQueue.value = [];
    isLiveMode.value = true;
    selectedMachineKey.value = null;
    selectedJobId.value = null;
    selectedAgvIndex.value = null;
  }

  /**
   * 向 Buffer 尾部追加一帧（SSE 实时推送 / 脚本驱动均使用此方法）。
   * 只有在 isLiveMode 为 true 时才自动跟进到最新帧，
   * 避免打断用户正在手动回放的操作。
   */
  function pushSnapshot(snapshot) {
    const frame = normalizeSnapshot(snapshot, historyBuffer.value.length);
    historyBuffer.value.push(frame);

    if (isLiveMode.value || isPlaying.value) {
      currentIndex.value = historyBuffer.value.length - 1;
    }
  }

  /**
   * 加载完整离线历史数据，替换整个 Buffer。
   */
  function loadData(data) {
    reset();
    historyBuffer.value = data;
    currentIndex.value = 0;
    isLiveMode.value = false;
  }

  /**
   * 标记"将要运行命令序列"（测试模式）。
   * 实际帧数据由外部通过 pushSnapshot 驱动写入。
   */
  function loadCommandQueue(queue) {
    reset();
    commandQueue.value = queue;
  }

  function togglePlay() {
    if (historyBuffer.value.length === 0) return;
    // 已到末尾时从头播放
    if (!isPlaying.value && currentIndex.value >= totalSteps.value - 1) {
      currentIndex.value = 0;
    }
    isPlaying.value = !isPlaying.value;
  }

  /**
   * 手动定位到某帧（用于进度条拖动）。
   * 离开尾部时退出 liveMode，回到尾部时重新进入。
   */
  function setIndex(val) {
    if (historyBuffer.value.length === 0) return;

    let index = parseInt(val, 10);
    if (isNaN(index)) index = 0;
    index = Math.max(0, Math.min(index, historyBuffer.value.length - 1));

    currentIndex.value = index;
    isLiveMode.value = index === historyBuffer.value.length - 1;
  }

  /**
   * 动画循环步进，由 requestAnimationFrame 驱动调用。
   * @returns {boolean} 是否成功步进（false 表示已到末尾或暂停）
   */
  function nextStep() {
    if (!isPlaying.value) return false;

    if (currentIndex.value < totalSteps.value - 1) {
      currentIndex.value++;
      return true;
    }

    isPlaying.value = false;
    return false;
  }

  /**
   * 初始化所有 AGV 到动画系统（写入初始快照）。
   * 只在 buffer 为空时执行，避免意外清除已有历史数据。
   */
  function initializeAGVs() {
    const agvs = getAGVs();
    if (agvs.length === 0) return;

    if (historyBuffer.value.length > 0) {
      console.warn(
        "[FactoryStore] initializeAGVs: buffer 非空，跳过初始化以保留现有数据。",
      );
      return;
    }

    const initialSnapshot = {
      timestamp: "T+0",
      env_timeline: "0",
      grid_state: {
        positions_xy: agvs.map((agv) => agv.initialLocation),
        is_active: agvs.map(() => true),
      },
      machines: {},
      active_transfers: [],
    };

    pushSnapshot(initialSnapshot);
  }

  // ══════════════════════════════════════════
  // 数据集缓存（首次请求后缓存在 Pinia）
  // ══════════════════════════════════════════
  const datasetList = ref(null);
  let _datasetPromise = null;

  async function fetchDatasets() {
    if (datasetList.value) return datasetList.value;
    if (_datasetPromise) return _datasetPromise;
    _datasetPromise = (async () => {
      try {
        const data = await apiGet(API_ROUTES.DATASET_LIST);
        datasetList.value = data;
        return data;
      } catch (e) {
        console.error('[FactoryStore] 加载数据集失败:', e);
        _datasetPromise = null;
        throw e;
      }
    })();
    return _datasetPromise;
  }

  // ══════════════════════════════════════════
  // 全量清理 (退出工厂时调用)
  // ══════════════════════════════════════════
  function clearAll() {
    // 动画状态
    reset();
    // 配置
    factoryConfigs.value = {};
    currentConfigId.value = null;
    runtimeExceptionConfig.value = null;
    runtimeProcessingTimeConfig.value = null;
    // 工厂选择仍保留 localStorage
    localStorage.removeItem(STORAGE_KEYS.SELECTED_FACTORY);
  }

  // ══════════════════════════════════════════
  // 公开接口
  // ══════════════════════════════════════════
  return {
    // ── 工厂列表 ──
    factories,
    selectedFactoryId,
    currentFactory,
    getFactories,
    setCurrentFactory,

    // ── 配置管理 ──
    factoryConfigs,
    currentConfigId,
    currentConfig,
    currentTopologyConfig,
    currentRenderConfig,
    runtimeExceptionConfig,
    runtimeProcessingTimeConfig,
    rebuildHint,
    loadConfigFromFile,
    setCurrentConfig,
    getLoadedConfigs,
    deleteConfig,
    setCurrentTopologyConfig,
    getAGVs,
    initializeAGVs,
    getCurrentAssets,
    getJobs,
    getJobMachineIdMap,
    getMachineRuntimeKey,
    getMachineConfig,
    getMachineDisplayName,
    getAssetsStats,
    formatAssetsList,
    addAssetFromTemplate,
    getOccupiedCells,
    isCellOccupied,
    updateAssetPosition,
    renameAsset,
    removeAsset,
    exportCurrentConfig,
    setRuntimeProfiles,

    // ── 动画状态 ──
    historyBuffer,
    commandQueue,
    currentIndex,
    isPlaying,
    isLiveMode,
    playbackSpeed,
    totalSteps,
    currentState,
    latestState,
    reset,
    clearAll,
    pushSnapshot,
    loadData,
    loadCommandQueue,
    togglePlay,
    setIndex,
    nextStep,

    // ── 模块① machine ↔ Job 联动 ──
    selectedMachineKey,
    selectedJobId,
    selectedAgvIndex,
    selectMachine,
    selectJob,
    selectAgv,

    // ── 数据集缓存 ──
    datasetList,
    fetchDatasets,
  };
});
