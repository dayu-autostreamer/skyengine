import { defineStore } from "pinia";
import { ref, computed } from "vue";

/**
 * 工厂管理和动画状态 (Unified Store)
 * 核心设计：所有动画帧都存储在 historyBuffer 中，无论是离线加载还是实时推送
 */

// 辅助函数：动态获取资源路径
function getAssetUrl(name) {
  if (!name) return "";
  return `/src/assets/factories/${name}`;
}
export const useFactoryStore = defineStore("factory", () => {
  // ============ 1. 工厂列表管理 (无需改动) ============
  // 工厂列表
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
    localStorage.getItem("selectedFactoryId") || "packet_factory",
  );

  const currentFactory = computed(() =>
    factories.value.find((f) => f.id === selectedFactoryId.value),
  );

  const setCurrentFactory = (factoryId) => {
    const factory = factories.value.find((f) => f.id === factoryId);
    if (factory) {
      selectedFactoryId.value = factoryId;
      localStorage.setItem("selectedFactoryId", factoryId);
    }
  };

  const getFactories = () => factories.value;

  // ============ 1.5. 工厂配置管理 (Factory Configuration) ============
  // 用户上传的工厂配置文件
  const factoryConfigs = ref({});
  // 当前选中的配置 ID
  const currentConfigId = ref(null);

  const currentConfig = computed(() => {
    if (!currentConfigId.value) return null;
    return factoryConfigs.value[currentConfigId.value];
  });

  const currentTopologyConfig = computed(() => {
    return currentConfig.value?.topology || null;
  });

  const currentRenderConfig = computed(() => {
    return (
      currentConfig.value?.renderConfig || {
        baseGridSize: 40,
        gridWidth: 20,
        gridHeight: 14,
        colors: {},
      }
    );
  });

  /**
   * 加载工厂配置文件
   * @param {Object} config - 验证过的配置对象
   */
  function loadConfigFromFile(config) {
    factoryConfigs.value[config.id] = config;
    currentConfigId.value = config.id;

    // 可选：保存到 localStorage
    localStorage.setItem("currentConfigId", config.id);
  }

  /**
   * 切换当前使用的配置
   */
  function setCurrentConfig(configId) {
    if (factoryConfigs.value[configId]) {
      currentConfigId.value = configId;
      localStorage.setItem("currentConfigId", configId);
    }
  }

  /**
   * 获取所有已加载的配置
   */
  function getLoadedConfigs() {
    return Object.values(factoryConfigs.value);
  }

  /**
   * 删除一个配置
   */
  function deleteConfig(configId) {
    delete factoryConfigs.value[configId];
    if (currentConfigId.value === configId) {
      currentConfigId.value = null;
    }
  }

  /**
   * 直接设置拓扑配置（用于从 JSON 加载或临时配置）
   * @param {Object} topologyData - 拓扑数据 { zones, machines, waypoints, baseGridSize, gridWidth, gridHeight }
   * @returns {string} 配置 ID
   */
  function setCurrentTopologyConfig(topologyData) {
    // 生成临时配置 ID（如果没有提供）
    const configId = topologyData.id || `temp_config_${Date.now()}`;

    // 创建完整的配置对象
    const completeConfig = {
      id: configId,
      name: topologyData.name || "临时配置",
      version: topologyData.version || "1.0",
      timestamp: Date.now(),
      topology: {
        zones: topologyData.zones || [],
        machines: topologyData.machines || {},
        waypoints: topologyData.waypoints || {},
        gridWidth: topologyData.gridWidth || 20,
        gridHeight: topologyData.gridHeight || 14,
      },
      agvs: (topologyData.agvs || []).map((agv) => ({
        id: agv.id,
        name: agv.name || `AGV-${agv.id}`,
        initialLocation: agv.initialLocation || [0, 0],
        velocity: agv.velocity || 1.0,
        capacity: agv.capacity || 100,
        status: agv.status || "IDLE",
      })),
      renderConfig: {
        baseGridSize: topologyData.baseGridSize || 40,
        gridWidth: topologyData.gridWidth || 20,
        gridHeight: topologyData.gridHeight || 14,
        colors: topologyData.colors || {},
      },
    };

    // 存储到配置库
    factoryConfigs.value[configId] = completeConfig;
    currentConfigId.value = configId;

    // 持久化当前配置 ID
    localStorage.setItem("currentConfigId", configId);

    return configId;
  }

  /**
   * 获取当前配置中的 AGV 列表
   * @returns {Array} AGV 配置数组
   */
  function getAGVs() {
    if (!currentConfig.value) {
      return [];
    }
    return currentConfig.value.agvs || [];
  }

  /**
   * 初始化 AGV 到动画系统（推送初始位置快照）
   */
  function initializeAGVs() {
    const agvs = getAGVs();
    if (agvs.length === 0) {
      return;
    }

    // 创建初始快照，包含所有 AGV 的初始位置
    const initialPositions = agvs.map((agv) => agv.initialLocation);
    const initialActiveStates = agvs.map(() => true);

    const initialSnapshot = {
      timestamp: "T+0",
      env_timeline: "0",
      grid_state: {
        positions_xy: initialPositions,
        is_active: initialActiveStates,
      },
      machines: {},
      active_transfers: [],
    };

    // 清除历史记录并推送初始帧
    reset();
    pushSnapshot(initialSnapshot);

    console.log(`✅ 已初始化 ${agvs.length} 个 AGV`);
  }

  /**
   * 获取当前配置中的所有资产（节点信息）
   * @returns {Object} { zones, machines, waypoints }
   */
  function getCurrentAssets() {
    if (!currentConfig.value) {
      return { zones: [], machines: {}, waypoints: {} };
    }
    return (
      currentConfig.value.topology || { zones: [], machines: {}, waypoints: {} }
    );
  }

  /**
   * 获取资产统计信息
   * @returns {Object} 统计数据
   */
  function getAssetsStats() {
    const assets = getCurrentAssets();
    return {
      zoneCount: (assets.zones || []).length,
      machineCount: Object.keys(assets.machines || {}).length,
      waypointCount: Object.keys(assets.waypoints || {}).length,
      totalAssets:
        (assets.zones || []).length +
        Object.keys(assets.machines || {}).length +
        Object.keys(assets.waypoints || {}).length,
    };
  }

  /**
   * 格式化资产列表（用于 UI 显示）
   * @returns {Array} 格式化的资产数组
   */
  function formatAssetsList() {
    const assets = getCurrentAssets();
    const list = [];

    // 添加区域
    if (assets.zones) {
      assets.zones.forEach((zone) => {
        list.push({
          type: "zone",
          icon: "🔒",
          name: zone.name || `Zone ${zone.id}`,
          description: `区域类型: ${zone.type || "unknown"}`,
          data: zone,
        });
      });
    }

    // 添加机器
    if (assets.machines) {
      Object.entries(assets.machines).forEach(([key, machine]) => {
        list.push({
          type: "machine",
          icon: "⚙️",
          name: machine.name || `Machine ${key}`,
          description: `状态: ${machine.status || "UNKNOWN"}`,
          data: machine,
        });
      });
    }

    // 添加路由点
    if (assets.waypoints) {
      Object.entries(assets.waypoints).forEach(([key, waypoint]) => {
        const icon = waypoint.type === "dock" ? "🚪" : "📍";
        list.push({
          type: "waypoint",
          icon: icon,
          name: waypoint.name || `Waypoint ${key}`,
          description: `类型: ${waypoint.type || "route"}`,
          data: waypoint,
        });
      });
    }

    return list;
  }

  // ============ 2. 核心动画状态 (Animation State) ============

  // 统一的数据源：历史帧队列
  const historyBuffer = ref([]);

  // 辅助状态：是否处于“命令模式”（用于 ControlPanel 判断是否显示“脚本运行中”）
  const commandQueue = ref([]);

  const currentIndex = ref(0);
  const isPlaying = ref(false);
  const playbackSpeed = ref(1000);

  // 计算属性：总步数
  const totalSteps = computed(() => historyBuffer.value.length);

  // 计算属性：当前帧状态 (UI 渲染源头)
  const currentState = computed(() => {
    // 安全回退：如果 Buffer 为空，返回默认空对象
    if (historyBuffer.value.length === 0) {
      return {
        env_timeline: "0",
        grid_state: { positions_xy: [], is_active: [] },
        machines: {},
        active_transfers: [],
      };
    }

    // 确保索引合法
    const idx = Math.min(currentIndex.value, historyBuffer.value.length - 1);
    return historyBuffer.value[idx];
  });

  // ============ 3. 动作方法 (Actions) ============

  /**
   * 重置所有状态
   */
  function reset() {
    isPlaying.value = false;
    currentIndex.value = 0;
    historyBuffer.value = []; // 清空数据源
    commandQueue.value = []; // 清空命令标记
  }

  /**
   * [核心] 向 Buffer 尾部追加一帧数据 (Push)
   * 适用于：SSE 实时推送、runFullSystemTest 脚本驱动
   */
  function pushSnapshot(snapshot) {
    // 1. 数据清洗与规范化
    const frame = {
      env_timeline: snapshot.timestamp || `T+${historyBuffer.value.length}`,
      grid_state: snapshot.grid_state || { positions_xy: [], is_active: [] },
      machines: snapshot.machines || {},
      active_transfers: snapshot.active_transfers || [],
      _meta: { wait: 0 }, // 可选元数据
    };

    // 2. 入队
    historyBuffer.value.push(frame);

    // 3. 自动跟进 (Live Mode 逻辑)
    // 如果当前正处于最新帧（或者正在播放中），则自动跳到新的一帧
    // 这样用户在查看历史数据时不会被强制打断
    if (
      isPlaying.value ||
      currentIndex.value >= historyBuffer.value.length - 2
    ) {
      currentIndex.value = historyBuffer.value.length - 1;
    }
  }

  /**
   * 加载完整历史数据 (离线回放模式)
   * 直接替换整个 Buffer
   */
  function loadData(data) {
    reset();
    historyBuffer.value = data;
    currentIndex.value = 0;
  }

  /**
   * 加载命令队列 (测试模式标记)
   * 注意：这里只是标记“我们将要运行这些命令”，实际的数据生成由 runFullSystemTest.js 驱动 pushSnapshot 完成
   */
  function loadCommandQueue(queue) {
    reset();
    commandQueue.value = queue; // 仅用于 UI 显示总进度或当前模式
    // 实际数据不在这里生成，而是等待 pushSnapshot
  }

  // 切换播放
  function togglePlay() {
    if (historyBuffer.value.length === 0) return;

    // 如果已到末尾，点击播放则重头开始
    if (!isPlaying.value && currentIndex.value >= totalSteps.value - 1) {
      currentIndex.value = 0;
    }
    isPlaying.value = !isPlaying.value;
  }

  // 手动拖动进度条
  function setIndex(val) {
    let index = parseInt(val);
    if (isNaN(index)) index = 0;
    if (index < 0) index = 0;
    if (index >= historyBuffer.value.length)
      index = historyBuffer.value.length - 1;

    currentIndex.value = index;
  }

  // 动画循环步进 (给 FactoryPlayerSSE 内部 requestAnimationFrame 用)
  function nextStep() {
    if (!isPlaying.value) return false;

    if (currentIndex.value < totalSteps.value - 1) {
      currentIndex.value++;
      return true;
    } else {
      isPlaying.value = false;
      return false;
    }
  }

  return {
    // State - Factories & Configs
    factories,
    selectedFactoryId,
    factoryConfigs,
    currentConfigId,

    // State - Animation
    historyBuffer, // 统一使用这个作为数据源
    commandQueue, // 用于 UI 判断模式
    currentIndex,
    isPlaying,
    playbackSpeed,

    // Getters - Factories & Configs
    currentFactory,
    currentConfig,
    currentTopologyConfig,
    currentRenderConfig,
    totalSteps,
    currentState,
    getFactories,
    getLoadedConfigs,

    // Actions - Factories & Configs
    setCurrentFactory,
    loadConfigFromFile,
    setCurrentConfig,
    deleteConfig,
    setCurrentTopologyConfig,
    getCurrentAssets,
    getAssetsStats,
    formatAssetsList,
    getAGVs,
    initializeAGVs,

    // Actions - Animation
    reset,
    pushSnapshot,
    loadData,
    loadCommandQueue,
    togglePlay,
    setIndex,
    nextStep,
  };
});
