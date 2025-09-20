<template>
  <div class="monitor-outline">
    <!-- 顶部标题 -->
    <h3>Runtime Monitor</h3>

    <!-- 总体指标区 -->
    <el-row :gutter="20" class="summary-row">
      <el-col :span="6">
        <el-card>
          <div class="summary-item">
            <div class="summary-label">System Status</div>
            <el-tag :type="systemStatus.type">{{ systemStatus.text }}</el-tag>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card>
          <div class="summary-item">
            <div class="summary-label">Active AGVs</div>
            <el-tag :type="activeAGVs.type">{{ activeAGVs.text }}</el-tag>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card>
          <div class="summary-item">
            <div class="summary-label">Completed Jobs</div>
            <el-tag :type="completedJobs.type">{{ completedJobs.text }}</el-tag>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card>
          <div class="summary-item">
            <div class="summary-label">Throughput</div>
            <el-tag :type="throughput.type">{{ throughput.text }}</el-tag>
          </div>
        </el-card>
      </el-col>
    </el-row>
    <!-- 资源监控区 -->
    <div class="section-title">Resource Usage</div>
    <el-row :gutter="20">
      <el-col :span="8">
        <el-card>
          <v-chart class="chart" :option="machineLoadOption"/>
        </el-card>
      </el-col>
      <el-col :span="8">
        <el-card>
          <v-chart class="chart" :option="agvLoadOption"/>
        </el-card>
      </el-col>
      <el-col :span="8">
        <el-card>
          <v-chart class="chart" :option="jobLatencyOption"/>
        </el-card>
      </el-col>
    </el-row>

    <!-- 吞吐量监控 -->
    <div class="section-title">System Throughput</div>
    <el-card>
      <v-chart class="chart" :option="throughputOption"/>
    </el-card>

    <!-- 日志 & 告警区 -->
    <div class="section-title">Logs & Alerts</div>
    <el-card class="log-card">
      <div v-for="(line, idx) in logs" :key="idx" class="log-line">
        {{ line }}
      </div>
    </el-card>
  </div>
</template>

<script setup>
import {ref, onMounted, onUnmounted} from "vue";
import {ElCard, ElRow, ElCol, ElTag} from "element-plus";
import VChart from "vue-echarts";
import {use} from "echarts/core";
import {LineChart, BarChart} from "echarts/charts";
import {CanvasRenderer} from "echarts/renderers";
import {TitleComponent, TooltipComponent, LegendComponent, GridComponent} from "echarts/components";

use([CanvasRenderer, LineChart, BarChart, TitleComponent, TooltipComponent, LegendComponent, GridComponent]);


const systemStatus = ref({text: "Running", type: "success"});
const activeAGVs = ref({text: "4", type: "primary"});
const completedJobs = ref({text: "12", type: "primary"});
const throughput = ref({text: "45 jobs/min", type: "primary"});


// 机器负载
const machineLoadOption = ref({
  title: {text: "Machine Load", left: "center"},
  xAxis: {type: "category", data: ["M1", "M2", "M3", "M4", "M5"]},
  yAxis: {type: "value"},
  series: [{data: [70, 55, 80, 40, 65], type: "bar"}]
});

// AGV 负载
const agvLoadOption = ref({
  title: {text: "AGV Load", left: "center"},
  xAxis: {type: "category", data: ["AGV1", "AGV2", "AGV3", "AGV4"]},
  yAxis: {type: "value"},
  series: [{data: [5, 7, 3, 6], type: "bar"}]
});

// 任务完成时延
const jobLatencyOption = ref({
  title: {text: "Job Completion Latency (s)", left: "center"},
  xAxis: {type: "category", data: ["Job1", "Job2", "Job3", "Job4", "Job5"]},
  yAxis: {type: "value"},
  series: [{data: [12, 18, 15, 20, 14], type: "line", smooth: true}]
});

// 系统吞吐量
const throughputOption = ref({
  title: {text: "Throughput Over Time", left: "center"},
  xAxis: {type: "category", data: ["1min", "2min", "3min", "4min", "5min"]},
  yAxis: {type: "value"},
  series: [{data: [40, 42, 45, 47, 50], type: "line", smooth: true}]
});

// 日志模拟
const logs = ref([
  "[INFO] AGV1 picked up Job23",
  "[INFO] Machine M2 started processing Job22",
  "[INFO] Job21 finished in 14s",
  "[WARN] AGV3 load > threshold",
  "[INFO] Throughput reached 45 jobs/min"
]);

let eventSource = null;

const updateMachineData = (data) => {
  machineLoadOption.value.series[0].data = data;
};
const updateAgvData = (data) => {
  agvLoadOption.value.series[0].data = data;
};
const updateJobData = (data) => {
  jobLatencyOption.value.series[0].data = data;
};
const updateThroughputData = (data) => {
  throughputOption.value.series[0].data = data;
};
const updateLogsData = (newLogs) => {
  logs.value = newLogs.slice(-50); // 只保留最近50条
};
const updateSummaryData = (data) => {
  systemStatus.value.text = data.systemStatus.text;
  systemStatus.value.type = data.systemStatus.type;

  activeAGVs.value.text = data.activeAGVs.text;
  activeAGVs.value.type = data.activeAGVs.type;

  completedJobs.value.text = data.completedJobs.text;
  completedJobs.value.type = data.completedJobs.type;

  throughput.value.text = data.throughput.text;
  throughput.value.type = data.throughput.type;
};
onMounted(() => {
  eventSource = new EventSource("http://localhost:8000/sse/monitor");
  eventSource.onmessage = (e) => {
    const parsed = JSON.parse(e.data);
    updateMachineData(parsed.machine);
    updateAgvData(parsed.agv);
    updateJobData(parsed.job);
    updateThroughputData(parsed.throughput);
    updateLogsData(parsed.logs);
    // 解析并更新 summary
    updateSummaryData({
      systemStatus: {
        text: parsed.systemStatus.text,
        type: parsed.systemStatus.type
      },
      activeAGVs: {
        text: parsed.activeAGVs.toString(),
        type: parsed.activeAGVs > 0 ? "primary" : "danger"
      },
      completedJobs: {
        text: parsed.completedJobs.toString(),
        type: "success"
      },
      throughput: {
        text: parsed.throughput + " jobs/min",
        type: parsed.throughput > 50 ? "success" : "warning"
      }
    });
  };
});

onUnmounted(() => {
  if (eventSource) eventSource.close();
});

</script>

<style scoped lang="scss">
.monitor-outline {
  padding: 20px;
  background-color: #fff;
  border-radius: 12px;
}

h3 {
  font-size: 24px;
  margin-bottom: 20px;
}

.section-title {
  font-size: 18px;
  font-weight: bold;
  margin: 20px 0 10px;
  color: #333;
}

.summary-row {
  margin-bottom: 20px;
}

.summary-item {
  text-align: center;

  .summary-label {
    font-size: 14px;
    color: #666;
    margin-bottom: 5px;
  }
}

.chart {
  width: 100%;
  height: 300px;
}

.log-card {
  max-height: 200px;
  overflow-y: auto;
  background: #1e1e1e;
  color: #dcdcdc;
  font-family: monospace;
  font-size: 13px;
}

.log-line {
  padding: 2px 0;
}
</style>
