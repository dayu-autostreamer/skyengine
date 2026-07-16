<template>
  <div class="factory-manage-container">
    <div class="middle-panel">
      <FactoryPlayerSSE
        :hide-control-panel="true"
        :edit-mode="isEditMode"
        :background-theme="backgroundTheme"
        :background-size="backgroundSize"
      />

      <div class="floating-toolbar-wrapper">
        <div class="floating-toolbar">
          <div class="toolbar-left">
            <span class="toolbar-title">🏭 容器化仿真工作台</span>
            <span class="divider">|</span>
            <span class="toolbar-label">状态: {{ containerStatus }}</span>
            <span class="divider">|</span>
            <span class="toolbar-label connection-status" :class="connectionStatus.scenario === '已连接'
              ? 'connected'
              : 'disconnected'
              ">
              引擎: {{ connectionStatus.scenario }}
            </span>
          </div>
          <div class="toolbar-right">
            <button @click="handleExecutePlan" class="glass-btn primary"
              :disabled="sim.isRunningTest.value || isStartingContainer" title="上传选中的方案">
              🚀 启动仿真
            </button>
          </div>
        </div>

        <!-- 容器启动加载状态 -->
        <div v-if="isStartingContainer" class="container-loading-bar">
          <div class="loading-spinner"></div>
          <span>正在启动仿真容器...</span>
          <span class="loading-detail">{{ containerStartStatus }}</span>
        </div>
      </div>
    </div>

    <FactoryTabsPanel
      :tabs="tabs"
      v-model="activeTab"
      v-model:show-panel="showPanel"
      :is-edit-mode="isEditMode"
      :is-running-test="sim.isRunningTest.value"
      factory-type="grid_factory"
      @edit-mode-change="isEditMode = $event"
    >
      <template #tab-simulation>
        <div class="simulation-tab">
          <div class="sim-field">
            <label>FJSP 排程</label>
            <select v-model="sim.selectedFjsp.value" class="plan-select" :disabled="sim.isRunningTest.value">
              <option v-for="opt in sim.fjspOptions.value" :key="opt.value" :value="opt.value">
                {{ opt.label }}
              </option>
            </select>
          </div>
          <div class="sim-field">
            <label>MAPF 路由</label>
            <select v-model="sim.selectedMapf.value" class="plan-select" :disabled="sim.isRunningTest.value">
              <option v-for="opt in sim.mapfOptions.value" :key="opt.value" :value="opt.value">
                {{ opt.label }}
              </option>
            </select>
          </div>
          <div class="sim-field">
            <label>任务分配</label>
            <select v-model="sim.selectedAssigner.value" class="plan-select" :disabled="sim.isRunningTest.value">
              <option v-for="opt in sim.assignerOptions.value" :key="opt.value" :value="opt.value">
                {{ opt.label }}
              </option>
            </select>
          </div>

          <div class="sim-btn-row">
            <button @click="handleExecutePlan" class="launch-btn" :disabled="sim.isRunningTest.value || isStartingContainer" title="一键执行：设定策略→重置→启动">
              🚀 启动
            </button>
            <button @click="handleStop" class="stop-btn" :disabled="!sim.isRunningTest.value" title="停止仿真并断开数据流">
              ⏹ 停止
            </button>
          </div>

          <div class="sim-divider"></div>

          <span class="test-label">分步调试</span>
          <div class="sim-btn-row">
            <button @click="testSetAlgorithm" class="step-btn" :disabled="sim.isRunningTest.value || isStartingContainer">
              1️⃣ 设定策略
            </button>
            <button @click="testReset" class="step-btn" :disabled="sim.isRunningTest.value || isStartingContainer">
              2️⃣ 重置工厂
            </button>
            <button @click="testPlay" class="step-btn" :disabled="sim.isRunningTest.value || isStartingContainer">
              3️⃣ 启动执行
            </button>
          </div>

          <div class="sim-divider"></div>

          <div class="sim-field">
            <label>场景风格</label>
            <select v-model="backgroundTheme" class="plan-select">
              <option value="clean">简洁</option>
              <option value="factory">工厂车间</option>
            </select>
          </div>
          <div v-if="backgroundTheme === 'factory'" class="sim-field">
            <label>厂房尺寸</label>
            <select v-model.number="backgroundSize" class="plan-select">
              <option :value="1">紧凑</option>
              <option :value="2">标准</option>
              <option :value="3">宽敞</option>
              <option :value="4">大厅</option>
            </select>
          </div>
        </div>
      </template>

      <template #tab-config>
        <ConfigPanel
          @edit-mode-change="isEditMode = $event"
          @config-loaded="handleConfigLoaded"
        >
          <template #data-source-extra>
            <div class="docker-config-exception-row">
              <label>异常场景</label>
              <select
                v-model="selectedExceptionPreset"
                class="plan-select docker-config-select"
                :disabled="sim.isRunningTest.value || exceptionConfigLocked"
                :title="exceptionConfigLocked ? '当前配置文件已提供 exception_config，异常场景固定为自定义' : '选择内置异常场景'"
              >
                <option v-for="opt in exceptionPresetOptions" :key="opt.value" :value="opt.value">
                  {{ opt.label }}
                </option>
              </select>
            </div>
            <div class="docker-config-exception-row">
              <label>加工时间波动</label>
              <select
                v-model="selectedProcessingTimePreset"
                class="plan-select docker-config-select"
                :disabled="sim.isRunningTest.value || processingTimeConfigLocked"
                :title="processingTimeConfigLocked ? '当前配置文件已提供 processing_time_config，加工时间波动固定为自定义' : '选择内置加工时间波动'"
              >
                <option v-for="opt in processingTimePresetOptions" :key="opt.value" :value="opt.value">
                  {{ opt.label }}
                </option>
              </select>
            </div>
            <div class="docker-config-exception-row">
              <label>停止条件</label>
              <div class="docker-step-limit-row">
                <input
                  v-model.number="maxSimulationSteps"
                  class="docker-step-input"
                  type="number"
                  min="1"
                  step="100"
                  :disabled="sim.isRunningTest.value || unlimitedSimulationSteps"
                />
                <label class="docker-checkbox-label">
                  <input
                    v-model="unlimitedSimulationSteps"
                    type="checkbox"
                    :disabled="sim.isRunningTest.value"
                  />
                  不限制（直到 Job 完成）
                </label>
              </div>
            </div>
          </template>
        </ConfigPanel>
      </template>

      <template #tab-experiment>
        <ExperimentWorkbenchPanel
          :is-running="sim.isRunningTest.value"
          :simulation-meta="currentExperimentMeta"
          :exception-config="activeExceptionConfig"
          :processing-time-config="activeProcessingTimeConfig"
          @load-plan="handleExperimentPlanLoaded"
        />
      </template>

      <template #tab-insert>
        <JobInsertPanel
          :is-running="sim.isRunningTest.value"
          :algorithm="sim.algorithmString.value"
          supports-insertion
        />
      </template>

      <!-- 指标 tab：配置驱动的 DashboardPanel -->
      <template #tab-metrics>
        <DashboardPanel :config="dashboardConfig" />
      </template>
    </FactoryTabsPanel>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, watch } from "vue";
import { ElMessage } from "element-plus";
import { useFactoryStore } from "@/stores/factory";
import { useMonitorStore } from "@/stores/monitor";
import { useAnalysisLogStore } from "@/stores/analysisLog";
import { apiPost, API_ROUTES, getApiUrl } from "@/utils/api";
import { sseManager } from "@/utils/sse";
import { useSimulationConfig } from "@/composables/useSimulationConfig";
import { getAlgorithmOptions } from "@/config/algorithms";

import FactoryPlayerSSE from "@/components/FactoryPlayerSSE.vue";
import FactoryTabsPanel from "@/components/FactoryTabsPanel.vue";
import ConfigPanel from "@/components/ConfigPanel.vue";
import DashboardPanel from "@/components/DashboardPanel.vue";
import JobInsertPanel from "@/components/JobInsertPanel.vue";
import ExperimentWorkbenchPanel from "@/components/ExperimentWorkbenchPanel.vue";
import dashboardConfig from "@/config/dashboards/docker_factory.json";

const store = useFactoryStore();
const monitorStore = useMonitorStore();
const analysisLog = useAnalysisLogStore();

const sim = useSimulationConfig({
  defaults: { fjsp: "pso", mapf: "mapf_gpt", assigner: "nearest" },
  defaultOptions: {
    fjsp: getAlgorithmOptions("fjsp"),
    mapf: getAlgorithmOptions("mapf"),
    assigner: getAlgorithmOptions("assigner"),
  },
});

// ==================== Docker 专属状态 ====================

const isEditMode = ref(false);
const isStartingContainer = ref(false);
const containerStartStatus = ref("");
const showPanel = ref(true);
let sseConnectionId = null;
let metricsConnectionId = null;
let eventsConnectionId = null;
const activeTab = ref("simulation");
const backgroundTheme = ref("factory");
const backgroundSize = ref(2);
const selectedExceptionPreset = ref("no_event");
const selectedProcessingTimePreset = ref("none");
const maxSimulationSteps = ref(1000);
const unlimitedSimulationSteps = ref(false);
const exceptionConfigLocked = computed(() => {
  const cfg = store.currentConfig?.exception_config;
  return Boolean(cfg && typeof cfg === "object");
});
const processingTimeConfigLocked = computed(() => {
  const cfg = store.currentConfig?.processing_time_config;
  return Boolean(cfg && typeof cfg === "object");
});
const exceptionPresetOptions = [
  { value: "no_event", label: "无异常" },
  { value: "mild_failure", label: "轻度故障" },
  { value: "moderate_failure", label: "中度故障" },
  { value: "stress_failure", label: "压力故障" },
  { value: "routing_disruption", label: "路径扰动" },
  { value: "custom", label: "自定义" },
];
const processingTimePresetOptions = [
  { value: "none", label: "无波动" },
  { value: "mild_variance", label: "轻微波动" },
  { value: "moderate_variance", label: "中等波动" },
  { value: "high_variance", label: "高波动" },
  { value: "custom", label: "自定义" },
];

const activeExceptionConfig = computed(() => getActiveExceptionConfig());
const activeProcessingTimeConfig = computed(() => getActiveProcessingTimeConfig());
const activeSimulationControl = computed(() => ({
  max_steps: unlimitedSimulationSteps.value ? null : normalizeMaxSimulationSteps(maxSimulationSteps.value),
}));
const currentExperimentMeta = computed(() => ({
  factory_id: store.selectedFactoryId,
  config_id: store.currentConfigId,
  fjsp: sim.selectedFjsp.value,
  mapf: sim.selectedMapf.value,
  assigner: sim.selectedAssigner.value,
  algorithm: sim.algorithmString.value,
  exception_preset: selectedExceptionPreset.value,
  processing_time_preset: selectedProcessingTimePreset.value,
  max_steps: activeSimulationControl.value.max_steps,
}));

const tabs = [
  { key: "simulation", label: "仿真", icon: "🚀" },
  { key: "control", label: "控制", icon: "⚙️" },
  { key: "config", label: "配置", icon: "🔧" },
  { key: "experiment", label: "实验", icon: "🧪" },
  { key: "insert", label: "插单", icon: "➕" },
  { key: "agent", label: "分析", icon: "🤖" },
  { key: "metrics", label: "指标", icon: "📊" },
  { key: "events", label: "日志", icon: "📋" },
];

const containerStatus = computed(() => {
  if (isStartingContainer.value) return '启动容器中...';
  if (sim.isRunningTest.value) return '运行中';
  return '就绪';
});

const connectionStatus = ref({
  control: "未连接",
  state: "未连接",
  metrics: "未连接",
  scenario: "未连接",
});

onMounted(async () => {
  store.reset();
  await sim.fetchAlgoOptions();
});

watch(
  () => store.currentConfig?.exception_config,
  (cfg) => {
    if (cfg && typeof cfg === "object") {
      selectedExceptionPreset.value = "custom";
    } else if (selectedExceptionPreset.value === "custom") {
      selectedExceptionPreset.value = "no_event";
    }
  },
);

watch(
  () => store.currentConfig?.processing_time_config,
  (cfg) => {
    if (cfg && typeof cfg === "object") {
      selectedProcessingTimePreset.value = "custom";
    } else if (selectedProcessingTimePreset.value === "custom") {
      selectedProcessingTimePreset.value = "none";
    }
  },
);

// ==================== 停止 ====================

const disconnectAllSSE = () => {
  if (sseConnectionId) {
    sseManager.disconnect(sseConnectionId);
    sseConnectionId = null;
  }
  if (metricsConnectionId) {
    sseManager.disconnect(metricsConnectionId);
    metricsConnectionId = null;
  }
  if (eventsConnectionId) {
    sseManager.disconnect(eventsConnectionId);
    eventsConnectionId = null;
  }
};

const resetLocalRuntimeState = ({ initializeAgvs = true } = {}) => {
  disconnectAllSSE();
  sim.isRunningTest.value = false;
  store.isPlaying = false;
  store.reset();
  monitorStore.clearSim();
  if (initializeAgvs) {
    store.initializeAGVs();
  }
};

const handleStop = async () => {
  // 1. 调后端 pause 让引擎停下
  try {
    await apiPost(API_ROUTES.FACTORY_CONTROL_PAUSE, null, { timeout: 15000 });
    ElMessage.success('⏹ 已停止仿真');
  } catch (error) {
    console.warn('[DockerFactory] pause 请求失败:', error.message);
    ElMessage.warning(`停止请求失败：${error.message}（数据流将本地断开）`);
  }
  // 2. 手动停止也先归档三流，避免插单记录随本地 reset 丢失。
  if (store.historyBuffer.length > 0) {
    try {
      await analysisLog.finalizeFromStores(store, monitorStore, {
        factory_id: store.selectedFactoryId,
        algorithm: sim.algorithmString.value,
      });
    } catch (error) {
      console.error('[DockerFactory] 手动停止归档失败:', error);
      ElMessage.warning(`运行日志保存失败：${error.message}`);
    }
  }
  // 3. 本地断 SSE + 重置状态
  resetLocalRuntimeState({ initializeAgvs: false });
};

// ==================== 执行方案 (Docker 3步模式) ====================

const handleExecutePlan = async () => {
  if (sim.isRunningTest.value) return;

  isStartingContainer.value = true;
  containerStartStatus.value = '正在设定策略...';

  try {
    await syncRunConfigToBackend();

    await apiPost(API_ROUTES.FACTORY_ALGORITHM_SET, {
      algorithm: sim.algorithmString.value,
    }, { timeout: 30000 });

    containerStartStatus.value = '正在重置环境...';
    await apiPost(API_ROUTES.FACTORY_CONTROL_RESET, null, { timeout: 30000 });

    containerStartStatus.value = '正在启动容器...';
    isStartingContainer.value = false;

    await testPlay();
  } catch (error) {
    isStartingContainer.value = false;
    sim.isRunningTest.value = false;
    ElMessage.error(`仿真执行失败: ${error.message}`);
  }
};

// ==================== 分步测试 API ====================

const testSetAlgorithm = async () => {
  try {
    await syncRunConfigToBackend();
    await apiPost(API_ROUTES.FACTORY_ALGORITHM_SET, {
      algorithm: sim.algorithmString.value,
    }, { timeout: 15000 });
    ElMessage.success(`✅ 设定策略成功: ${sim.algorithmString.value}`);
  } catch (error) {
    ElMessage.error(`❌ 设定策略失败: ${error.message}`);
  }
};

const testReset = async () => {
  try {
    resetLocalRuntimeState({ initializeAgvs: false });
    await syncRunConfigToBackend();
    await apiPost(API_ROUTES.FACTORY_CONTROL_RESET, null, { timeout: 15000 });
    store.initializeAGVs();
    ElMessage.success('✅ 重置工厂成功');
  } catch (error) {
    ElMessage.error(`❌ 重置工厂失败: ${error.message}`);
  }
};

const testPlay = async () => {
  // 1. 先建立所有 SSE 连接（不依赖 play 是否成功）
  //    DockerProxy.start() 首次启动 mapf/fjsp 容器可能 > 30s，
  //    如果 SSE 放在 await play 之后，play 超时会导致 SSE 永远不建立。
  try {
    await syncRunConfigToBackend();
  } catch (error) {
    ElMessage.error(`运行配置同步失败: ${error.message}`);
    return;
  }
  disconnectAllSSE();
  store.reset();
  monitorStore.clearSim();

  sim.isRunningTest.value = true;
  store.isPlaying = true;

  const stateUrl = getApiUrl(API_ROUTES.STREAM_STATE);
  console.log('[DockerFactory] 建立 state SSE:', stateUrl);
  sseConnectionId = sseManager.connect(stateUrl, {
    eventTypes: ['state'],
    eventHandlers: {
      state: (data) => {
        if (data.status === 'idle' || data.status === 'no_factory' || data.status === 'error') {
          return;
        }
        if (data.frame) {
          store.pushSnapshot(data.frame);
          monitorStore.pushSimFrameEvents(data.frame.events, data.frame.env_timeline);
        }
        if (data.status === 'stopped' || data.status === 'finished') {
          console.log('[DockerFactory] 仿真完成');
          if (sseConnectionId) {
            sseManager.disconnect(sseConnectionId);
            sseConnectionId = null;
          }
          store.isPlaying = false;
          sim.isRunningTest.value = false;
          // episode 闭环：深拷贝三流 → POST /analysis/runs 入库
          // 失败仅打 log，不阻塞 UI（用户已能看到 episode 完成）
          analysisLog.finalizeFromStores(store, monitorStore, {
            factory_id: store.selectedFactoryId,
          }).catch((e) => console.error('[DockerFactory] finalizeFromStores 失败:', e));
          return;
        }
      },
    },
    onError: (error) => {
      console.error('[DockerFactory] state SSE error:', error);
    },
  });
  console.log('[DockerFactory] state SSE 已创建:', sseConnectionId);

  const metricsUrl = getApiUrl(API_ROUTES.STREAM_METRICS);
  metricsConnectionId = sseManager.connect(metricsUrl, {
    eventTypes: ['metrics'],
    eventHandlers: {
      metrics: (data) => {
        monitorStore.pushSimMetrics(data);
        if (data.status === 'stopped' && metricsConnectionId) {
          sseManager.disconnect(metricsConnectionId);
          metricsConnectionId = null;
        }
      },
    },
    onError: (error) => {
      console.error('[DockerFactory] metrics SSE error:', error);
    },
  });
  console.log('[DockerFactory] metrics SSE 已创建:', metricsConnectionId);

  const eventsUrl = getApiUrl(API_ROUTES.STREAM_EVENTS);
  eventsConnectionId = sseManager.connect(eventsUrl, {
    eventTypes: ['event'],
    eventHandlers: {
      event: (data) => {
        monitorStore.pushSimEvent(data);
      },
    },
    onError: (error) => {
      console.error('[DockerFactory] events SSE error:', error);
    },
  });
  console.log('[DockerFactory] events SSE 已创建:', eventsConnectionId);

  // 2. 发送 play 请求（首次可能 > 30s，用 120s 兜底）
  try {
    const resp = await apiPost(API_ROUTES.FACTORY_CONTROL_PLAY, null, { timeout: 120000 });
    if (resp?.run_id) {
      monitorStore.startRun({ runId: resp.run_id, factoryType: 'grid_factory' });
    }
    ElMessage.success('✅ 启动执行成功');
  } catch (error) {
    // play 超时不断开 SSE — DockerProxy 仍在后台跑，engine 最终会产 frame
    console.warn('[DockerFactory] play 请求超时或失败，SSE 保持连接等待:', error.message);
    ElMessage.warning(`play 请求超时，SSE 保持连接等待数据...`);
  }
};

function handleConfigLoaded(config) {
  resetLocalRuntimeState();
  if (config && Object.prototype.hasOwnProperty.call(config, "simulation_control")) {
    applySimulationControl(config.simulation_control);
  }
  if (config?.exception_config) {
    selectedExceptionPreset.value = "custom";
  } else if (selectedExceptionPreset.value === "custom") {
    selectedExceptionPreset.value = "no_event";
  }
  if (config?.processing_time_config) {
    selectedProcessingTimePreset.value = "custom";
  } else if (selectedProcessingTimePreset.value === "custom") {
    selectedProcessingTimePreset.value = "none";
  }
}

function handleExperimentPlanLoaded(plan) {
  const config = plan?.config ? JSON.parse(JSON.stringify(plan.config)) : null;
  if (config) {
    if (plan.exception_config) {
      config.exception_config = JSON.parse(JSON.stringify(plan.exception_config));
    }
    if (plan.processing_time_config) {
      config.processing_time_config = JSON.parse(JSON.stringify(plan.processing_time_config));
    }
    resetLocalRuntimeState();
    store.loadConfigFromFile(config);
    store.initializeAGVs();
    selectedExceptionPreset.value = config.exception_config ? "custom" : "no_event";
    selectedProcessingTimePreset.value = config.processing_time_config ? "custom" : "none";
    applySimulationControl(config.simulation_control ?? plan?.simulation);
  }
  const meta = plan?.simulation || {};
  if (meta.fjsp) sim.selectedFjsp.value = meta.fjsp;
  if (meta.mapf) sim.selectedMapf.value = meta.mapf;
  if (meta.assigner) sim.selectedAssigner.value = meta.assigner;
  applySimulationControl(config?.simulation_control ?? meta);
}

async function syncRunConfigToBackend() {
  const currentConfig = store.currentConfig;
  if (!currentConfig) return;
  const config = JSON.parse(JSON.stringify(currentConfig));
  config.exception_config = getActiveExceptionConfig();
  config.processing_time_config = getActiveProcessingTimeConfig();
  store.setRuntimeProfiles({
    exceptionConfig: config.exception_config,
    processingTimeConfig: config.processing_time_config,
  });
  config.simulation_control = {
    ...(config.simulation_control || {}),
    ...activeSimulationControl.value,
  };
  const response = await apiPost(API_ROUTES.FACTORY_CONFIG_UPLOAD, {
    filename: `${config.name || config.id || "grid_factory_new"}.json`,
    config,
  }, { timeout: 30000 });
  if (response.status !== "ok") {
    throw new Error(response.message || "运行配置同步失败");
  }
}

function getActiveExceptionConfig() {
  if (exceptionConfigLocked.value || selectedExceptionPreset.value === "custom") {
    const cfg = store.currentConfig?.exception_config;
    return cfg ? JSON.parse(JSON.stringify(cfg)) : { preset: "no_event" };
  }
  return { preset: selectedExceptionPreset.value };
}

function getActiveProcessingTimeConfig() {
  if (processingTimeConfigLocked.value || selectedProcessingTimePreset.value === "custom") {
    const cfg = store.currentConfig?.processing_time_config;
    return cfg ? JSON.parse(JSON.stringify(cfg)) : { preset: "none" };
  }
  return { preset: selectedProcessingTimePreset.value };
}

function normalizeMaxSimulationSteps(value) {
  const n = Number(value);
  if (!Number.isFinite(n)) return 1000;
  return Math.max(1, Math.floor(n));
}

function applySimulationControl(control) {
  if (!control || typeof control !== "object") {
    unlimitedSimulationSteps.value = false;
    maxSimulationSteps.value = 1000;
    return;
  }
  const raw = control?.max_steps;
  if (raw === null || raw === "unlimited" || raw === "infinite") {
    unlimitedSimulationSteps.value = true;
    return;
  }
  unlimitedSimulationSteps.value = false;
  if (raw !== undefined) {
    maxSimulationSteps.value = normalizeMaxSimulationSteps(raw);
  }
}

onUnmounted(() => {
  disconnectAllSSE();
  sim.cleanup(store);
});
</script>

<style scoped>
@import "../styles/FactoryManage.css";

.container-loading-bar {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 16px;
  background: rgba(60, 120, 200, 0.15);
  border: 1px solid rgba(100, 180, 255, 0.3);
  border-radius: 8px;
  margin-top: 8px;
}

.loading-spinner {
  width: 16px;
  height: 16px;
  border: 2px solid rgba(100, 180, 255, 0.3);
  border-top-color: #64b5ff;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.loading-detail {
  color: #64b5ff;
  font-size: 12px;
}

.simulation-tab .step-btn {
  flex: 1;
  padding: 7px 0;
  font-size: 12px;
  font-weight: 500;
  border: 1px solid rgba(100, 180, 255, 0.25);
  border-radius: 6px;
  background: rgba(60, 120, 200, 0.18);
  color: rgba(200, 220, 255, 0.9);
  cursor: pointer;
  transition: all 0.2s ease;
}

.simulation-tab .step-btn:hover:not(:disabled) {
  background: rgba(60, 120, 200, 0.38);
  border-color: rgba(100, 180, 255, 0.55);
  color: #ffffff;
  box-shadow: 0 0 12px rgba(100, 180, 255, 0.18);
}

.simulation-tab .step-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.simulation-tab .test-label {
  color: rgba(160, 190, 230, 0.6);
  font-size: 10px;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  margin-bottom: 4px;
  display: block;
}

.sim-divider {
  height: 1px;
  background: rgba(255, 255, 255, 0.1);
  margin: 10px 0;
}

.simulation-tab .sim-help {
  display: block;
  margin-top: 4px;
  color: rgba(160, 190, 230, 0.58);
  font-size: 10px;
  line-height: 1.35;
}

.docker-config-exception-row {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.docker-config-exception-row > label {
  font-size: 11px;
  font-weight: 500;
  color: rgba(160, 190, 230, 0.5);
}

.docker-config-select {
  width: 100%;
}

.docker-step-limit-row {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.docker-step-input {
  flex: 0 0 120px;
  min-width: 0;
  padding: 7px 10px;
  border: 1px solid rgba(100, 180, 255, 0.15);
  background: rgba(20, 25, 45, 0.6);
  border-radius: 6px;
  color: rgba(200, 220, 255, 0.9);
  font-size: 12px;
  outline: none;
}

.docker-step-input:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.docker-checkbox-label {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  color: rgba(200, 220, 255, 0.82);
  font-size: 12px;
  line-height: 1.4;
}

.docker-checkbox-label input {
  margin: 0;
}

</style>
