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
            <span class="toolbar-title">🏗️ 静态工厂管理</span>
            <span class="divider">|</span>
            <span class="toolbar-label">状态: {{ isRunningTest ? "运行中..." : "就绪" }}</span>
            <span class="divider">|</span>
            <span class="toolbar-label connection-status" :class="connectionStatus.scenario === '已连接'
              ? 'connected'
              : 'disconnected'
              ">
              静态场景: {{ connectionStatus.scenario }}
            </span>
          </div>
          <div class="toolbar-right">
            <select v-model="selectedEnvironment" class="plan-select" :disabled="isRunningTest">
              <option value="simulation">仿真环境</option>
              <option value="real">真实现场环境</option>
            </select>
            <select v-model="selectedAlgorithm" class="plan-select" :disabled="isRunningTest">
              <option value="default">默认布局方案</option>
              <option value="greedy">优化布局方案</option>
            </select>
            <button @click="handleExecutePlan" class="glass-btn primary" :disabled="isRunningTest" title="执行选中的方案">
              🚀 执行
            </button>
          </div>
        </div>
      </div>
    </div>

    <RightSidePanel ref="rightSidePanelRef" config-panel-title="⚙️ 静态配置" :show-chart="true"
      event-panel-title="📋 系统日志" />
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from "vue";
import { ElMessage } from "element-plus";
import { useFactoryStore } from "@/stores/factory";
import { useMonitorStore } from "@/stores/monitor";
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

onMounted(async () => {
  // 静态工厂初始化生命周期
  console.log("✅ StaticFactoryManager 已挂载");

  // 初始化多连接管理器
  const factoryId = store.selectedFactoryId;
  connectionManager = createFactoryConnectionManager(factoryId);

  await connectionManager.init(
    {
      // 通用处理器（兜底使用）
      onStateUpdate: (data, eventType) => {
        console.log(`[StaticFactory] 状态更新 [${eventType}]:`, data);
        if (data.snapshot) {
          store.pushSnapshot(data.snapshot);
        }
      },
      onMetricsUpdate: (data, eventType) => {
        console.log(`[StaticFactory] 指标更新 [${eventType}]:`, data);
        if (data.metrics) {
          monitorStore.pushMetrics(data.metrics);
        }
      },
      onControlError: (error) => {
        console.error("[StaticFactory] 控制错误:", error);
        ElMessage.error("静态工厂控制连接异常");
      },
    },
    {
      // 自定义要监听的事件类型（包括 fallback 事件）
      state: ['grid_state', 'state'],  // grid_state 为主，state 为 fallback
      metrics: ['grid_metrics', 'metrics'],  // grid_metrics 为主，metrics 为 fallback
      control: ['command_response', 'control'],  // command_response 为主，control 为 fallback
    },
    {
      // 为不同事件类型指定专属处理器
      state: {
        'grid_state': (data) => {
          console.log('📍 接收到完整状态快照', data);

          // 检查数据状态
          if (data.status === 'idle') {
            console.log('⏸️ 工厂空闲中，等待执行...');
            return;
          }

          if (data.status === 'error') {
            console.error('❌ 状态数据错误:', data.message);
            ElMessage.error(`状态错误: ${data.message}`);
            return;
          }

          // 后端已经按照 fullSystemTest.js 的格式返回数据
          // 直接推送到 store
          store.pushSnapshot(data);

          // 如果有事件，推送到监控
          if (data.events && data.events.length > 0) {
            data.events.forEach(event => {
              monitorStore.pushEvent({
                title: event.title,
                message: event.message,
                type: event.type,
                idx: data.step || 0
              });
            });
          }
        },
        'state': (data) => {
          // 处理默认的 state 事件（fallback）
          if (data.status === 'idle') {
            console.log('⏸️ [Fallback] 工厂空闲');
          }
        }
      },
      metrics: {
        'grid_metrics': (data) => {
          // 检查数据状态
          if (data.status === 'idle') {
            console.log('⏸️ 指标空闲中');
            return;
          }

          if (data.status === 'error') {
            console.error('❌ 指标数据错误:', data.message);
            return;
          }

          console.log('📊 接收到指标数据', data);
          // 后端已经按照 fullSystemTest.js 的格式返回数据
          // 直接推送到监控 store
          monitorStore.pushMetrics(data);
        },
        'metrics': (data) => {
          // 处理默认的 metrics 事件（fallback）
          if (data.status === 'idle') {
            console.log('⏸️ [Fallback] 指标空闲');
          }
        }
      },
      control: {
        'command_response': (data) => {
          console.log('✅ 命令响应', data);
          // 更新连接状态

          // 监控运行状态
          if (data.status === 'stopped' && isRunningTest.value) {
            isRunningTest.value = false;
            ElMessage.success('✅ 执行完成！');
          }
        },
        'control': (data) => {
          // 处理默认的 control 事件（fallback）
          console.log('🎮 [Fallback] 控制状态', data);
        }
      },
    }
  );

});


/**
 * 执行方案
 */
const handleExecutePlan = async () => {
  if (isRunningTest.value) return;

  const environment = selectedEnvironment.value;
  const algorithm = selectedAlgorithm.value;

  console.log(`执行方案: 环境=${environment}, 算法=${algorithm}`);

  // 检查场景连接
  if (!connectionManager.isScenarioConnected) {
    ElMessage.error("❌ 未连接到后端场景，无法执行");
    return;
  }

  try {
    isRunningTest.value = true;

    // 执行重置命令
    await connectionManager.executeControl("reset");
    ElMessage.success("✅ 已发送重置命令到后端");

    // 根据算法类型执行对应的计划
    await connectionManager.executeControl("play", { algorithm });
    ElMessage.success(
      `✅ 已启动 ${algorithm === "default" ? "默认" : "优化"} 布局方案，通过 SSE 接收数据`,
    );

    // 注意：不再调用本地的 runFullSystemTest
    // 数据将通过 SSE 连接从后端实时推送

  } catch (error) {
    ElMessage.error(`❌ 执行计划失败: ${error.message}`);
    isRunningTest.value = false;
  }
};

onUnmounted(() => {
  // 清理连接和测试
  console.log("🛑 StaticFactoryManager 卸载，清理连接和测试");
  if (stopTest) stopTest();
  if (eventSource) sseManager.disconnect(eventSource);
  if (connectionManager) connectionManager.disconnect();
});
</script>
<style scoped>
@import "../styles/FactoryManage.css";
</style>
