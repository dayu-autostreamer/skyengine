import { defineStore } from "pinia";
import { ref, computed } from "vue";

// ─────────────────────────────────────────────
// 常量
// ─────────────────────────────────────────────
const STORAGE_KEYS = {
  SELECTED_FACTORY: "selectedFactoryId",
  CURRENT_CONFIG_ID: "currentConfigId",
  FACTORY_CONFIGS: "factoryConfigs",
};

const DEFAULT_RENDER_CONFIG = Object.freeze({
  baseGridSize: 40,
  gridWidth: 20,
  gridHeight: 14,
  colors: {},
});

const EMPTY_GRID_STATE = Object.freeze({
  env_timeline: "0",
  grid_state: { positions_xy: [], is_active: [] },
  machines: {},
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
 * 安全读取 localStorage，解析失败时返回 fallback。
 */
function readStorage(key, fallback = null) {
  try {
    const raw = localStorage.getItem(key);
    if (raw === null) return fallback;
    return JSON.parse(raw);
  } catch {
    return fallback;
  }
}

/**
 * 安全写入 localStorage，序列化失败时静默跳过。
 */
function writeStorage(key, value) {
  try {
    localStorage.setItem(key, JSON.stringify(value));
  } catch (e) {
    console.warn(`[FactoryStore] 无法写入 localStorage (${key}):`, e);
  }
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
 */
function normalizeSnapshot(snapshot, fallbackIndex) {
  return {
    env_timeline:
      snapshot.timestamp ?? snapshot.env_timeline ?? `T+${fallbackIndex}`,
    grid_state: snapshot.grid_state ?? { positions_xy: [], is_active: [] },
    machines: snapshot.machines ?? {},
    active_transfers: snapshot.active_transfers ?? [],
  };
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
  const factoryConfigs = ref(
    (() => {
      const saved = readStorage(STORAGE_KEYS.FACTORY_CONFIGS, {});
      // 过滤损坏条目
      return Object.fromEntries(
        Object.entries(saved).filter(([, v]) => validateConfig(v)),
      );
    })(),
  );

  const currentConfigId = ref(
    readStorage(STORAGE_KEYS.CURRENT_CONFIG_ID, null),
  );

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
   * 持久化所有配置到 localStorage（每次变更后调用）。
   */
  function _persistConfigs() {
    writeStorage(STORAGE_KEYS.FACTORY_CONFIGS, factoryConfigs.value);
  }

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
    writeStorage(STORAGE_KEYS.CURRENT_CONFIG_ID, config.id);
    _persistConfigs();
  }

  function setCurrentConfig(configId) {
    if (!factoryConfigs.value[configId]) {
      console.warn(`[FactoryStore] 未找到配置 ID: ${configId}`);
      return;
    }
    currentConfigId.value = configId;
    writeStorage(STORAGE_KEYS.CURRENT_CONFIG_ID, configId);
  }

  function getLoadedConfigs() {
    return Object.values(factoryConfigs.value);
  }

  function deleteConfig(configId) {
    delete factoryConfigs.value[configId];
    if (currentConfigId.value === configId) {
      currentConfigId.value = null;
      writeStorage(STORAGE_KEYS.CURRENT_CONFIG_ID, null);
    }
    _persistConfigs();
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
    writeStorage(STORAGE_KEYS.CURRENT_CONFIG_ID, configId);
    _persistConfigs();

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

  function getAssetsStats() {
    const { zones = [], machines = {}, waypoints = {} } = getCurrentAssets();
    const zoneCount = zones.length;
    const machineCount = Object.keys(machines).length;
    const waypointCount = Object.keys(waypoints).length;
    return {
      zoneCount,
      machineCount,
      waypointCount,
      totalAssets: zoneCount + machineCount + waypointCount,
    };
  }

  function formatAssetsList() {
    const { zones = [], machines = {}, waypoints = {} } = getCurrentAssets();
    const list = [];

    zones.forEach((zone) => {
      list.push({
        type: "zone",
        icon: "🔒",
        name: zone.name ?? `Zone ${zone.id}`,
        description: `区域类型: ${zone.type ?? "unknown"}`,
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

    return list;
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

  // ──────────────────────────────────────────
  // 动画动作
  // ──────────────────────────────────────────

  function reset() {
    isPlaying.value = false;
    currentIndex.value = 0;
    historyBuffer.value = [];
    commandQueue.value = [];
    isLiveMode.value = true;
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
    console.log(`✅ 已初始化 ${agvs.length} 个 AGV`);
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
    loadConfigFromFile,
    setCurrentConfig,
    getLoadedConfigs,
    deleteConfig,
    setCurrentTopologyConfig,
    getAGVs,
    initializeAGVs,
    getCurrentAssets,
    getAssetsStats,
    formatAssetsList,

    // ── 动画状态 ──
    historyBuffer,
    commandQueue,
    currentIndex,
    isPlaying,
    isLiveMode,
    playbackSpeed,
    totalSteps,
    currentState,
    reset,
    pushSnapshot,
    loadData,
    loadCommandQueue,
    togglePlay,
    setIndex,
    nextStep,
  };
});