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
            <div class="summary-label">activeMachines</div>
            <el-tag :type="activeMachines.type">{{
                activeMachines.text
              }}
            </el-tag>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card>
          <div class="summary-item">
            <div class="summary-label">Total Jobs</div>
            <el-tag :type="totalJobs.type">{{ totalJobs.text }}</el-tag>
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
import {ref, onMounted, onUnmounted, onUpdated} from "vue";
import {ElCard, ElRow, ElCol, ElTag} from "element-plus";
import VChart from "vue-echarts";
import {use} from "echarts/core";
import {LineChart, BarChart} from "echarts/charts";
import {CanvasRenderer} from "echarts/renderers";
import {
  TitleComponent,
  TooltipComponent,
  LegendComponent,
  GridComponent,
} from "echarts/components";

use([
  CanvasRenderer,
  LineChart,
  BarChart,
  TitleComponent,
  TooltipComponent,
  LegendComponent,
  GridComponent,
]);

// Online success、Offline danger
const systemStatus = ref({text: "offline", type: "danger"});
const activeAGVs = ref({text: "0", type: "danger"});
const activeMachines = ref({text: "0", type: "danger"});

const totalJobs = ref({text: "0", type: "danger"});

// 机器负载
const machineLoadOption = ref({
  title: {text: "Machine Load", left: "center"},
  xAxis: {type: "category", data: ["M1", "M2", "M3", "M4", "M5"]},
  yAxis: {type: "value"},
  series: [{data: [70, 55, 80, 40, 65], type: "bar"}],
});

// AGV 负载
const agvLoadOption = ref({
  title: {text: "AGV Load", left: "center"},
  xAxis: {type: "category", data: ["AGV1", "AGV2", "AGV3", "AGV4"]},
  yAxis: {type: "value"},
  series: [{data: [5, 7, 3, 6], type: "bar"}],
});

// 任务完成时延
const jobLatencyOption = ref({
  title: {text: "Job Completion Latency (s)", left: "center"},
  xAxis: {type: "category", data: ["Job1", "Job2", "Job3", "Job4", "Job5"]},
  yAxis: {type: "value"},
  series: [{data: [12, 18, 15, 20, 14], type: "line", smooth: true}],
});

// 系统吞吐量
const throughputOption = ref({
  title: {text: "Throughput Over Time", left: "center"},
  xAxis: {type: "category", data: ["1min", "2min", "3min", "4min", "5min"]},
  yAxis: {type: "value"},
  series: [{data: [40, 42, 45, 47, 50], type: "line", smooth: true}],
});

const logs = ref(["[INFO] I AM AN EXAMPLE LOG"]);

const updateMachineData = (machine_list) => {
  // machineLoadOption.value.series[0].data = data;
   machineLoadOption.value.xAxis.data = machine_list.map(
      (series) => `MACHINE_${series.at(-1).value.machine_id}`
  );

  // 最新值：每个 AGV 最后一条 transport_count
  machineLoadOption.value.series[0].data = machine_list.map(
      (series) => series.at(-1).value.process_count
  );
};
const updateAgvData = (agv_list) => {
  // 横坐标：AGV 名字
  agvLoadOption.value.xAxis.data = agv_list.map(
      (series) => `AGV_${series.at(-1).value.agv_id}`
  );

  // 最新值：每个 AGV 最后一条 transport_count
  agvLoadOption.value.series[0].data = agv_list.map(
      (series) => series.at(-1).value.transport_count
  );
};
const updateJobData = (job_list) => {
  // 横坐标：Job 名字
  jobLatencyOption.value.xAxis.data = job_list.map(
      (series) => `Job_${series.at(-1).value.job_id}`
  );

  // 最新值：每个 Job 最后一条 completion_time
  jobLatencyOption.value.series[0].data = job_list.map(
      (series) => series.at(-1).value.total_delay
  );
};
// 下面这俩暂时没实现...todo 后续实现吞吐量和日志
// const updateThroughputData = (throughput_list) => {
//   // 横坐标：时间标签
//   throughputOption.value.xAxis.data = throughput_list.map(
//       (series) => `${series.at(-1).value.timestamp}min`
//   );
//
//   // 最新值：每个时间点的 throughput 值
//   throughputOption.value.series[0].data = throughput_list.map(
//       (series) => series.at(-1).value.throughput
//   );
// };
// const updateLogsData = (newLogs) => {
//   logs.value = newLogs.slice(-50); // 只保留最近50条
// };
const updateSummaryData = (data) => {
  systemStatus.value.text = data.systemStatus.text;
  systemStatus.value.type = data.systemStatus.type;

  activeAGVs.value.text = data.activeAGVs.text;
  activeAGVs.value.type = data.activeAGVs.type;

  activeMachines.value.text = data.activeMachines.text;
  activeMachines.value.type = data.activeMachines.type;

  totalJobs.value.text = data.totalJobs.text;
  totalJobs.value.type = data.totalJobs.type;
};

let eventSourceSystem = null;
let eventSourceAGV = null;
let eventSourceMachine = null;
let eventSourceJob = null;

const startEventSource = () => {
  const backendUrl = import.meta.env.VITE_BACKEND_ADDRESS;
  // 监控系统相关信息
  eventSourceSystem = new EventSource(backendUrl + "/monitor/system");
  // 连接成功，标记 online
  eventSourceSystem.onopen = () => {
    updateSummaryData({
      systemStatus: {
        text: "online",
        type: "success",
      },
    });
  };
  // 收到消息时，更新状态
  eventSourceSystem.onmessage = (e) => {
    const parsed = JSON.parse(e.data);
    updateSummaryData({
      systemStatus: {
        text: parsed.systemStatus ?? "online",
        type: "success",
      },
      activeAGVs: {
        text: parsed.activeAGVs,
        type: "success",
      },
      totalJobs: {
        text: parsed.totalJobs,
        type: "success",
      },
      activeMachines: {
        text: parsed.activeMachines,
        type: "success",
      },
    });
  };
  // 出错时，标记 offline
  eventSourceSystem.onerror = () => {
    updateSummaryData({
      systemStatus: {
        text: "offline",
        type: "danger",
      },
      activeAGVs: {
        text: "0",
        type: "danger",
      },
      completedJobs: {
        text: "0",
        type: "danger",
      },
      throughput: {
        text: "0",
        type: "danger",
      },
    });
  };
  // 监控组件指标
  eventSourceAGV = new EventSource(backendUrl + "/monitor/agv");
  eventSourceMachine = new EventSource(backendUrl + "/monitor/machine");
  eventSourceJob = new EventSource(backendUrl + "/monitor/job");

  eventSourceAGV.onmessage = (e) => {
    const parsed = JSON.parse(e.data);
    console.log("AGV data:", parsed.data);
    updateAgvData(parsed.data);
  };

  eventSourceMachine.onmessage = (e) => {
    const parsed = JSON.parse(e.data);
    console.log("Machine data:", parsed.data);
    updateMachineData(parsed.data);
  };

  eventSourceJob.onmessage = (e) => {
    const parsed = JSON.parse(e.data);
    console.log("Job data:", parsed.data);
    updateJobData(parsed.data);
  };
}

const clearEventSource = () => {
  if (eventSourceSystem) {
    eventSourceSystem.close();
    eventSourceSystem = null;
  }
  if (eventSourceAGV) {
    eventSourceAGV.close();
    eventSourceAGV = null;
  }
  if (eventSourceMachine) {
    eventSourceMachine.close();
    eventSourceMachine = null;
  }
  if (eventSourceJob) {
    eventSourceJob.close();
    eventSourceJob = null;
  }
}
onMounted(() => {
  startEventSource()
})

onUpdated(() => {
  startEventSource()
})

// 离开页面时关闭连接，避免内存泄漏
onUnmounted(() => {
  clearEventSource()
});

// updateMachineData(parsed.machine);
// updateAgvData(parsed.agv);
// updateJobData(parsed.job);
// updateThroughputData(parsed.throughput);
// updateLogsData(parsed.logs);
// activeAGVs: {
//   text: parsed.activeAGVs.toString(),
//   type: parsed.activeAGVs > 0 ? "primary" : "danger"
// },
// completedJobs: {
//   text: parsed.completedJobs.toString(),
//   type: "success"
// },
// throughput: {
//   text: parsed.throughput + " jobs/min",
//   type: parsed.throughput > 50 ? "success" : "warning"
// }
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
