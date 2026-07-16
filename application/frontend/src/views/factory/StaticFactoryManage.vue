<template>
  <div class="factory-manage-container">
    <div class="middle-panel">
      <FactoryPlayerSSE
        :hide-control-panel="true"
        :edit-mode="isEditMode"
        :background-theme="backgroundTheme"
        :background-size="backgroundSize"
      />
    </div>

    <FactoryTabsPanel
      :tabs="tabs"
      v-model="activeTab"
      v-model:show-panel="showPanel"
      :is-edit-mode="isEditMode"
      :is-running-test="sim.isRunningTest.value"
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
            <button @click="handleExecute" class="launch-btn" :disabled="sim.isRunningTest.value">
              🚀 执行
            </button>
            <button @click="sim.handleStop(store)" class="stop-btn" :disabled="!sim.isRunningTest.value">
              ⏹ 停止
            </button>
          </div>

          <div class="sim-field" style="margin-top: 4px">
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

      <!-- 模块②：指标 tab 用配置驱动的 DashboardPanel 替代默认 MetricsPanel -->
      <template #tab-metrics>
        <DashboardPanel :config="dashboardConfig" />
      </template>

      <template #tab-insert>
        <JobInsertPanel :is-running="false" :supports-insertion="false" />
      </template>
    </FactoryTabsPanel>
  </div>
</template>

<script setup>
import { ref, onUnmounted } from "vue";
import { useFactoryStore } from "@/stores/factory";
import { useMonitorStore } from "@/stores/monitor";
import { useSimulationConfig } from "@/composables/useSimulationConfig";
import FactoryPlayerSSE from "@/components/FactoryPlayerSSE.vue";
import FactoryTabsPanel from "@/components/FactoryTabsPanel.vue";
import DashboardPanel from "@/components/DashboardPanel.vue";
import JobInsertPanel from "@/components/JobInsertPanel.vue";
import dashboardConfig from "@/config/dashboards/static_factory.json";

const store = useFactoryStore();
const monitorStore = useMonitorStore();

const sim = useSimulationConfig({
  defaults: { fjsp: "pso", mapf: "mapf_gpt", assigner: "nearest" },
  defaultOptions: {
    fjsp: [
      { label: "PSO 粒子群", value: "pso" },
      { label: "DE 差分进化", value: "de" },
      { label: "DRL 深度强化学习", value: "drl" },
      { label: "BEST 最优搜索", value: "best" },
    ],
    mapf: [
      { label: "A* 路由", value: "astar" },
      { label: "GPT 路由", value: "mapf_gpt" },
    ],
    assigner: [
      { label: "FIFO 先来先服务", value: "fifo" },
      { label: "贪心分配", value: "greedy" },
      { label: "匈牙利算法", value: "hungarian" },
      { label: "最小拥堵", value: "least_congestion" },
      { label: "负载均衡", value: "load_balance" },
      { label: "最近分配", value: "nearest" },
      { label: "随机分配", value: "random" },
      { label: "SJT 最短作业", value: "sjt" },
      { label: "紧迫度优先", value: "urgency" },
    ],
  },
});

const isEditMode = ref(false);
const showPanel = ref(true);
const activeTab = ref("simulation");
const backgroundTheme = ref("factory");
const backgroundSize = ref(2);

const tabs = [
  { key: "simulation", label: "仿真", icon: "🚀" },
  { key: "control", label: "控制", icon: "⚙️" },
  { key: "config", label: "配置", icon: "🔧" },
  { key: "insert", label: "插单", icon: "➕" },
  { key: "agent", label: "分析", icon: "🤖" },
  { key: "metrics", label: "指标", icon: "📊" },
  { key: "events", label: "日志", icon: "📋" },
];

function handleExecute() {
  sim.handleExecutePlan(store, monitorStore, { mode: "frontend" });
}

onUnmounted(() => sim.cleanup(store));
</script>

<style scoped>
@import "../styles/FactoryManage.css";
</style>
