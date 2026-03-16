<template>
  <div class="factory-manage-container">
    <div class="left-panel">
      <ControlPanel />
    </div>

    <div class="middle-panel">
      <FactoryPlayerSSE :hide-control-panel="true" />

      <div class="floating-toolbar-wrapper">
        <div class="floating-toolbar">
          <div class="toolbar-left">
            <span class="toolbar-title">🏭 仿真工作台</span>
            <span class="divider">|</span>
            <span class="toolbar-label">状态: {{ isRunningTest ? "运行中..." : "就绪" }}</span>
            <span class="divider">|</span>
            <span class="toolbar-label connection-status" :class="connectionStatus.scenario === '已连接'
              ? 'connected'
              : 'disconnected'
              ">
              现场场景: {{ connectionStatus.scenario }}
            </span>
          </div>
          <div class="toolbar-right">
            <select v-model="selectedEnvironment" class="plan-select" :disabled="isRunningTest">
              <option value="simulation">仿真环境</option>
              <option value="real">真实现场环境</option>
            </select>
            <select v-model="selectedAlgorithm" class="plan-select" :disabled="isRunningTest">
              <option v-for="algo in algorithmOptions" :key="algo.value" :value="algo.value">
                {{ algo.label }}
              </option>
            </select>
            <button @click="handleExecutePlan" class="glass-btn primary" :disabled="isRunningTest" title="上传选中的方案">
              🚀 上传选中方案
            </button>
          </div>
        </div>

        <!-- API 测试按钮组 -->
        <div class="api-test-toolbar">
          <span class="test-label">API 测试:</span>
          <button @click="testSetAlgorithm" class="test-btn" :disabled="isRunningTest" title="测试设定调度策略">
            1️⃣ 设定策略
          </button>
          <button @click="testReset" class="test-btn" :disabled="isRunningTest" title="测试重置工厂">
            2️⃣ 重置工厂
          </button>
          <button @click="testPlay" class="test-btn" :disabled="isRunningTest" title="测试启动执行">
            3️⃣ 启动执行
          </button>
        </div>
      </div>
    </div>

    <RightSidePanel ref="rightSidePanelRef" config-panel-title="⚙️ 仿真配置" :show-chart="true"
      event-panel-title="📋 系统日志" />
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from "vue";
import { ElMessage } from "element-plus";
import { useFactoryStore } from "@/stores/factory";
import { useMonitorStore } from "@/stores/monitor";
import { backendSystemTest } from "@/scenarios/backendSystemTest";
import { apiPost, API_ROUTES } from "@/utils/api";

import FactoryPlayerSSE from "@/components/FactoryPlayerSSE.vue";
import ControlPanel from "@/components/ControlPanel.vue";
import RightSidePanel from "@/components/RightSidePanel.vue";

const store = useFactoryStore();
const monitorStore = useMonitorStore();

// 清理函数引用
let stopTest = null;

// 算法配置列表：后续可以从后端 API 获取
const algorithmOptions = ref([
  { label: '默认生产运输', value: 'default' },
  { label: '贪心算法优化', value: 'greedy' },
  { label: '强化学习 (PPO)', value: 'rl_ppo' },
  { label: '多代理协同 (MAPF)', value: 'mapf_v2' }
]);


const isRunningTest = ref(false);
const selectedEnvironment = ref("simulation");
const selectedAlgorithm = ref("default");
const connectionStatus = ref({
  control: "未连接",
  state: "未连接",
  metrics: "未连接",
  scenario: "未连接",
});

let eventSource = null;
let connectionManager = null;

onMounted(async () => {
  // 工厂初始化生命周期：
  console.log("✅ GridFactory 已挂载");

  // 获取后端算法配置列表
  try {
    const data = await apiPost(API_ROUTES.ALGO, {});
    if (Array.isArray(data)) {
      algorithmOptions.value = data;
    }
  } catch (error) {
    console.warn("[GridFactory] 获取算法列表失败，使用默认值:", error);
  }

  // 如果想默认选中第一个
  if (algorithmOptions.value.length > 0) {
    selectedAlgorithm.value = algorithmOptions.value[0].value;
  }
});



/**
 * 执行方案
 */
const handleExecutePlan = async () => {
  if (isRunningTest.value) return;

  const environment = selectedEnvironment.value;
  const algorithm = selectedAlgorithm.value;

  console.log(`执行方案: 环境=${environment}, 算法=${algorithm}`);

  // 如果选择真实环境，检查场景连接
  if (environment === "real") {
    // todo: 这里应该检查，确保已连接到真实场景
    ElMessage.error("❌ 未连接到真实场景，无法执行实时调度");
    return;
  } else {
    // 仿真环境：通过 SSE 与后端交互
    isRunningTest.value = true;
    try {
      // 保存返回的清理函数
      stopTest = await backendSystemTest(store, monitorStore, { algorithm }, () => {
        isRunningTest.value = false;
        stopTest = null;  // 清理完成后置空
        ElMessage.success("✅ 仿真执行完成");
      });
    } catch (error) {
      isRunningTest.value = false;
      stopTest = null;
      ElMessage.error(`仿真执行失败: ${error.message}`);
    }
  }
};

/**
 * 测试 API 1: 设定调度策略
 */
const testSetAlgorithm = async () => {
  const algorithm = selectedAlgorithm.value;
  console.log('[Test] Step 1: 设定调度策略...', { algorithm });
  try {
    const result = await apiPost(API_ROUTES.FACTORY_ALGORITHM_SET, { algorithm }, { timeout: 15000 });
    console.log('[Test] Step 1 完成:', result);
    ElMessage.success(`✅ 设定策略成功: ${algorithm}`);
  } catch (error) {
    console.error('[Test] Step 1 失败:', error);
    ElMessage.error(`❌ 设定策略失败: ${error.message}`);
  }
};

/**
 * 测试 API 2: 重置工厂
 */
const testReset = async () => {
  console.log('[Test] Step 2: 发送重置命令...');
  try {
    const result = await apiPost(API_ROUTES.FACTORY_CONTROL_RESET, null, { timeout: 15000 });
    console.log('[Test] Step 2 完成:', result);
    ElMessage.success('✅ 重置工厂成功');
  } catch (error) {
    console.error('[Test] Step 2 失败:', error);
    ElMessage.error(`❌ 重置工厂失败: ${error.message}`);
  }
};

/**
 * 测试 API 3: 启动执行
 */
const testPlay = async () => {
  console.log('[Test] Step 3: 发送启动命令...');
  try {
    const result = await apiPost(API_ROUTES.FACTORY_CONTROL_PLAY, null, { timeout: 15000 });
    console.log('[Test] Step 3 完成:', result);
    ElMessage.success('✅ 启动执行成功');
  } catch (error) {
    console.error('[Test] Step 3 失败:', error);
    ElMessage.error(`❌ 启动执行失败: ${error.message}`);
  }
};

onUnmounted(() => {
  // 清理连接和测试
  console.log("🛑 FactoryManage 卸载，清理连接和测试");
  if (stopTest) {
    stopTest();
    stopTest = null;
  }
});
</script>
<style scoped>
@import "../styles/FactoryManage.css";

.api-test-toolbar {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  background: rgba(30, 30, 40, 0.85);
  border-radius: 8px;
  margin-top: 8px;
  border: 1px solid rgba(255, 255, 255, 0.1);
  pointer-events: auto;
  /* 恢复点击事件，因为父元素 wrapper 设置了 pointer-events: none */
}

.test-label {
  color: #a0a0a0;
  font-size: 12px;
  margin-right: 4px;
}

.test-btn {
  padding: 6px 12px;
  font-size: 12px;
  border: 1px solid rgba(100, 180, 255, 0.3);
  border-radius: 6px;
  background: rgba(60, 120, 200, 0.2);
  color: #b0d0ff;
  cursor: pointer;
  transition: all 0.2s ease;
}

.test-btn:hover:not(:disabled) {
  background: rgba(60, 120, 200, 0.4);
  border-color: rgba(100, 180, 255, 0.6);
  color: #ffffff;
}

.test-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
</style>
