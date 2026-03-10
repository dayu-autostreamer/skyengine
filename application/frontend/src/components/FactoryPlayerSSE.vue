<template>
  <div class="layout-container">

    <div class="main-content">
      <div v-if="!hideControlPanel" class="panel-area">
        <ControlPanel />
      </div>

      <div class="vis-area" :class="{ 'full-width': hideControlPanel }">
        <div v-if="!configLoaded" class="config-placeholder">
          <div class="placeholder-content">
            <div class="placeholder-icon">⚙️</div>
            <h2>待配置工厂环境</h2>
            <p>请在右侧面板上传工厂配置文件（JSON格式）</p>
            <p class="hint">或调用 initializeConfig() 以加载本地配置</p>
          </div>
        </div>
        <FactoryVisualization v-else :static-config="topologyConfig" :baseGridSize="renderConfig.baseGridSize"
          :defaultGridWidth="renderConfig.gridWidth" :defaultGridHeight="renderConfig.gridHeight">
          <template #header>
            <div class="floating-toolbar">
              <div class="toolbar-left">
                <span class="toolbar-title">🏭 仿真工作台</span>
                <span class="divider">|</span>
                <span class="toolbar-label">当前场景: {{ currentScenario === 'safety' ? '安全巡检' : '未选择' }}</span>
              </div>

              <div class="toolbar-right">
                <button v-if="onLoadData" @click="onLoadData" class="glass-btn" title="加载测试数据">
                  📂 加载数据
                </button>
                <button @click="loadSafetyInspection" class="glass-btn"
                  :class="{ active: currentScenario === 'safety' }">
                  📂 加载安全巡检案例
                </button>
              </div>
            </div>
          </template>
        </FactoryVisualization>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue';
import { useFactoryStore } from '@/stores/factory';
import ControlPanel from './ControlPanel.vue';
import FactoryVisualization from './FactoryVisualization.vue';

const props = defineProps({
  hideControlPanel: {
    type: Boolean,
    default: false
  },
  onLoadData: {
    type: Function,
    default: null
  }
});

const store = useFactoryStore();
const currentScenario = ref('');
const configLoaded = ref(false);
const configError = ref(null);

/**
 * 从 JSON 配置文件加载工厂拓扑
 * @param {string} configPath - 配置文件路径（如 '/configs/packet_factory.json'）
 * @returns {Promise<Object>} 解析后的拓扑配置
 */
async function loadTopologyFromJson(configPath) {
  try {
    const response = await fetch(configPath);
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }

    const config = await response.json();

    // 验证必要字段
    if (!config.topology || !config.topology.zones || !config.topology.machines || !config.topology.waypoints) {
      throw new Error('配置文件缺少必要的 topology 字段');
    }

    // 处理 zones（确保每个 zone 都有必要字段）
    const zones = config.topology.zones.map(zone => ({
      id: zone.id,
      name: zone.name || '未命名区域',
      area: zone.area,
      type: zone.type || 'workarea',
      color: zone.color || 'rgba(0, 0, 0, 0.1)'
    }));

    // 处理 machines（转换对象为标准格式）
    const machines = {};
    Object.entries(config.topology.machines).forEach(([key, machine]) => {
      machines[key] = {
        id: machine.id || key,
        name: machine.name || `Machine ${key}`,
        location: machine.location,
        size: machine.size || [2, 2],
        status: machine.status || 'IDLE'
      };
    });

    // 处理 waypoints（转换对象为标准格式）
    const waypoints = {};
    Object.entries(config.topology.waypoints).forEach(([key, waypoint]) => {
      waypoints[key] = {
        id: waypoint.id || key,
        location: waypoint.location,
        type: waypoint.type || 'route',
        name: waypoint.name || `Waypoint ${key}`
      };
    });

    const parsedConfig = {
      zones,
      machines,
      waypoints,
      baseGridSize: config.renderConfig?.baseGridSize || 40,
      gridWidth: config.topology?.gridWidth || 20,
      gridHeight: config.topology?.gridHeight || 14
    };

    console.log('✅ 工厂配置加载成功:', config.name);
    configError.value = null;
    return parsedConfig;
  } catch (error) {
    const errorMsg = `配置加载失败: ${error.message}`;
    console.error('❌', errorMsg);
    configError.value = errorMsg;
    throw error;
  }
}

/**
 * 初始化配置（从 JSON 或使用默认硬编码配置）
 */
async function initializeConfig(configPath = '/configs/packet_factory.json') {
  try {
    const loadedConfig = await loadTopologyFromJson(configPath);
    // 更新 Store 中的配置
    const configId = store.setCurrentTopologyConfig(loadedConfig)
    configLoaded.value = true
    console.log(`✅ 配置已加载: ${configId}`)
  } catch (error) {
    console.warn('⚠️ 配置加载失败，请在右侧面板上传配置文件');
    configLoaded.value = false;
  }
}

// --- 默认空配置（等待用户上传）---
const defaultTopologyConfig = {
  zones: [],
  machines: {},
  waypoints: {}
};

// --- 1. 响应式拓扑配置 ---
// 优先使用已加载的配置，否则使用默认配置
const topologyConfig = computed(() => {
  return store.currentTopologyConfig || defaultTopologyConfig;
});

// 获取渲染配置（包括网格尺寸）
const renderConfig = computed(() => {
  const topology = store.currentTopologyConfig
  const renderCfg = store.currentRenderConfig
  return {
    baseGridSize: renderCfg?.baseGridSize || 40,
    gridWidth: topology?.gridWidth || renderCfg?.gridWidth || 20,
    gridHeight: topology?.gridHeight || renderCfg?.gridHeight || 14
  };
});

// --- 2. 动态任务数据 (Test Cases) ---
const safetyTestCase = [
  { x: 5, y: 2, label: "1. 初始上货 (Loading)", wait: 1000 },
  { x: 5, y: 4, label: "2. 前往 R1 路由点", wait: 0 },
  { x: 8, y: 4, label: "3. T1 顶部供料", wait: 800 },
  { x: 5, y: 4, label: "4. 退回 R1 路由点", wait: 0 },
  { x: 5, y: 6, label: "5. 前往 R2 路由点", wait: 0 },
  { x: 7, y: 6, label: "6. T1 左上工位", wait: 800 },
  { x: 7, y: 9, label: "7. T1 左下工位", wait: 800 },
  { x: 5, y: 9, label: "8. 退回主通道", wait: 0 },
  { x: 5, y: 11, label: "9. 前往底部通道", wait: 0 },
  { x: 13, y: 9, label: "10. T2 左下工位", wait: 800 },
  { x: 13, y: 6, label: "11. T2 左上工位", wait: 800 },
  { x: 17, y: 6, label: "12. 绕行右侧路由", wait: 0 },
  { x: 17, y: 4, label: "13. 准备进入顶部", wait: 0 },
  { x: 14, y: 4, label: "14. T2 顶部供料", wait: 1000 },
  { x: 5, y: 2, label: "15. 返回上货点", wait: 0 }
];

// --- 3. 业务逻辑方法 ---

function loadSafetyInspection() {
  currentScenario.value = 'safety';
  store.reset();
  store.loadCommandQueue(safetyTestCase);
}

// 监听 Store 中的拓扑配置变化
watch(() => store.currentConfigId, (newConfigId) => {
  if (newConfigId) {
    configLoaded.value = true;
    console.log(`✅ 配置已切换，地图已更新: ${newConfigId}`);
    
    // 自动初始化 AGV
    setTimeout(() => {
      store.initializeAGVs();
    }, 100);
  }
}, { immediate: true });

// 监听拓扑配置的深层变化
watch(() => store.currentTopologyConfig, (newConfig) => {
  if (newConfig && Object.keys(newConfig).length > 0) {
    configLoaded.value = true;
  }
}, { deep: true });

onMounted(() => {
  // 自动从 JSON 配置文件加载拓扑
  // initializeConfig('/configs/packet_factory.json');

  // 可选：初始化时不加载任何 Case，或者默认选中一个
  // loadSafetyInspection(); 
});
</script>

<style scoped>
@import './styles/FactoryPlayerSSE.css';

.config-placeholder {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 100%;
  height: 100%;
  background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
}

.placeholder-content {
  text-align: center;
  padding: 40px;
  background: white;
  border-radius: 12px;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
  max-width: 400px;
}

.placeholder-icon {
  font-size: 64px;
  margin-bottom: 20px;
}

.placeholder-content h2 {
  margin: 0 0 12px 0;
  color: #333;
  font-size: 20px;
}

.placeholder-content p {
  margin: 8px 0;
  color: #666;
  font-size: 13px;
  line-height: 1.6;
}

.placeholder-content p.hint {
  color: #999;
  font-size: 11px;
  margin-top: 16px;
}
</style>
