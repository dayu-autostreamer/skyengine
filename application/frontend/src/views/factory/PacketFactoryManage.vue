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
            <span class="toolbar-title">📦 包裹工厂管理</span>
            <span class="divider">|</span>
            <span class="toolbar-label"
              >状态: {{ isRunningTest ? "运行中..." : "就绪" }}</span
            >
            <span class="divider">|</span>
            <span
              class="toolbar-label connection-status"
              :class="
                connectionStatus.scenario === '已连接'
                  ? 'connected'
                  : 'disconnected'
              "
            >
              包裹场景: {{ connectionStatus.scenario }}
            </span>
          </div>
          <div class="toolbar-right">
            <select
              v-model="selectedEnvironment"
              class="plan-select"
              :disabled="isRunningTest"
            >
              <option value="simulation">仿真环境</option>
              <option value="real">真实现场环境</option>
            </select>
            <select
              v-model="selectedAlgorithm"
              class="plan-select"
              :disabled="isRunningTest"
            >
              <option value="default">默认路由策略</option>
              <option value="greedy">优化路由策略</option>
            </select>
            <button
              @click="handleExecutePlan"
              class="glass-btn primary"
              :disabled="isRunningTest"
              title="执行选中的方案"
            >
              🚀 执行
            </button>
          </div>
        </div>
      </div>
    </div>

    <RightSidePanel
      ref="rightSidePanelRef"
      config-panel-title="⚙️ 包裹配置"
      :show-chart="true"
      event-panel-title="📋 系统日志"
    />
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from "vue";
import { ElMessage } from "element-plus";
import { useFactoryStore } from "@/stores/factory";
import { useMonitorStore } from "@/stores/monitor";
import { runFullSystemTest } from "@/scenarios/fullSystemTest";
import { sseManager } from "@/utils/sse";
import { createFactoryConnectionManager } from "@/utils/factoryConnection";

import FactoryPlayerSSE from "@/components/FactoryPlayerSSE.vue";
import ControlPanel from "@/components/ControlPanel.vue";
import RightSidePanel from "@/components/RightSidePanel.vue";

const store = useFactoryStore();
const monitorStore = useMonitorStore();

const isRunningTest = ref(false);
const selectedEnvironment = ref("simulation");
const selectedAlgorithm = ref("default");
const connectionStatus = ref({
  control: "未连接",
  state: "未连接",
  metrics: "未连接",
  scenario: "未连接",
});

let stopTest = null;
let eventSource = null;
let connectionManager = null;

onMounted(() => {
  // 包裹工厂初始化生命周期
  console.log("✅ PacketFactoryManage 已挂载");

  // 初始化多连接管理器
  const factoryId = store.selectedFactoryId;
  connectionManager = createFactoryConnectionManager(factoryId);

  connectionManager.init(
    {
      onStateUpdate: (data, eventType) => {
        console.log(`[PacketFactory] 状态更新 [${eventType}]:`, data);
        // 可以在这里更新 store 的状态
        if (data.snapshot) {
          store.pushSnapshot(data.snapshot);
        }
      },
      onMetricsUpdate: (data, eventType) => {
        console.log(`[PacketFactory] 指标更新 [${eventType}]:`, data);
        // 更新监控数据
        if (data.metrics) {
          monitorStore.pushMetrics(data.metrics);
        }
      },
      onControlError: (error) => {
        console.error("[PacketFactory] 控制错误:", error);
        ElMessage.error("包裹工厂控制连接异常");
      },
    },
    {
      // 为Packet工厂自定义事件类型
      state: ['packet_state', 'package_update', 'route_update'],
      metrics: ['packet_metrics', 'delivery_rate', 'route_efficiency'],
      control: ['packet_control', 'command_response'],
    }
  );

  // 更新连接状态显示
  updateConnectionStatus();
});

const updateConnectionStatus = () => {
  if (connectionManager) {
    connectionStatus.value = connectionManager.getStatus();
  }
};

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
    if (!connectionManager.isScenarioConnected) {
      ElMessage.error("❌ 未连接到真实场景，无法执行实时调度");
      return;
    }

    try {
      isRunningTest.value = true;
      // 执行控制命令
      await connectionManager.executeControl("reset");
      ElMessage.success("✅ 已发送重置命令到后端");

      // 根据算法类型执行对应的计划
      await connectionManager.executeControl("play", { algorithm });
      ElMessage.success(
        `✅ 已发送 ${algorithm === "default" ? "默认" : "优化"} 路由策略执行命令`,
      );
    } catch (error) {
      ElMessage.error(`❌ 执行计划失败: ${error.message}`);
    } finally {
      isRunningTest.value = false;
    }
  } else {
    // 仿真环境：使用本地模拟
    isRunningTest.value = true;
    try {
      stopTest = runFullSystemTest(store, monitorStore, () => {
        isRunningTest.value = false;
        stopTest = null;
        ElMessage.success("✅ 仿真执行完成");
      });
    } catch (error) {
      isRunningTest.value = false;
      ElMessage.error(`仿真执行失败: ${error.message}`);
    }
  }
};

onUnmounted(() => {
  // 清理连接和测试
  console.log("🛑 PacketFactoryManage 卸载，清理连接和测试");
  if (stopTest) stopTest();
  if (eventSource) sseManager.disconnect(eventSource);
  if (connectionManager) connectionManager.disconnect();
});
</script>
<style scoped>
@import "../styles/FactoryManage.css";
</style>
