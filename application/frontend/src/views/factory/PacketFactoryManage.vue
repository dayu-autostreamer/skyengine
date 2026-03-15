<template>
  <div class="factory-manage-container">
    <!-- 左侧面板 - 配置与控制 -->
    <div class="left-panel">

      <!-- 主控制面板 -->
      <el-card style="margin-top: 15px">
        <template #header>
          <ElRow>
            <ElCol :span="8">
              <span>Control Panel</span>
            </ElCol>
            <ElCol :span="16">
              <el-select v-model="selectedFactory" placeholder="Select Factory" size="small" style="width: 100%">
                <el-option
                    v-for="factory in stores.factoryList"
                    :key="factory.id"
                    :label="'Factory: ' + factory.id"
                    :value="factory.id"
                />
              </el-select>
            </ElCol>
          </ElRow>
        </template>
        <el-row :gutter="10" class="mb-2">
          <el-col :span="6">
            <el-button type="primary" @click="handleFactoryRender" style="width: 100%">Render</el-button>
          </el-col>
          <el-col :span="6">
            <el-button type="success" @click="handleFactoryStart" style="width: 100%">Start</el-button>
          </el-col>
          <el-col :span="6">
            <el-button type="warning" @click="handleFactoryPause" style="width: 100%">Pause</el-button>
          </el-col>
          <el-col :span="6">
            <el-button type="danger" @click="handleFactoryReset" style="width: 100%">Reset</el-button>
          </el-col>
        </el-row>
        <div class="mb-2">
          <div style="text-align: center; margin-bottom: 6px;">Speed Level: {{ speedLevel }}</div>
          <el-slider v-model="speedLevel" :min="1" :max="10" show-input size="small" @change="changeSpeed"/>
        </div>
      </el-card>

      <!-- AGV 控制 -->
      <el-card style="margin-top: 15px">
        <template #header><span>AGV Control</span></template>
        <el-row :gutter="8" class="mb-2">
          <el-col :span="16">
            <el-select v-model="selectedAgv" placeholder="Select AGV" size="small" style="width: 100%">
              <el-option
                  v-for="agv in agvList"
                  :key="agv.id"
                  :label="'AGV' + agv.id"
                  :value="agv.id"
              />
            </el-select>
          </el-col>
          <el-col :span="8">
            <el-button-group style="width: 100%">
              <el-button @click="pauseAgv" type="warning" size="small" style="flex: 1">Pause</el-button>
              <el-button @click="resumeAgv" type="success" size="small" style="flex: 1">Go</el-button>
            </el-button-group>
          </el-col>
        </el-row>
      </el-card>

      <!-- Machine 控制 -->
      <el-card style="margin-top: 15px">
        <template #header><span>Machine Control</span></template>
        <el-row :gutter="8" class="mb-2">
          <el-col :span="16">
            <el-select v-model="selectedMachine" placeholder="Select Machine" size="small" style="width: 100%">
              <el-option
                  v-for="machine in machineList"
                  :key="machine.id"
                  :label="'Machine' + machine.id"
                  :value="machine.id"
              />
            </el-select>
          </el-col>
          <el-col :span="8">
            <el-button-group style="width: 100%">
              <el-button @click="pauseMachine" type="warning" size="small" style="flex: 1">Pause</el-button>
              <el-button @click="resumeMachine" type="success" size="small" style="flex: 1">Go</el-button>
            </el-button-group>
          </el-col>
        </el-row>
      </el-card>

      <!-- Job 控制 -->
      <el-card style="margin-top: 15px">
        <template #header><span>Job Control</span></template>
        <el-row :gutter="8">
          <el-col :span="16">
            <el-select v-model="selectedJob" placeholder="Select Job" size="small" style="width: 100%">
              <el-option
                  v-for="job in jobList"
                  :key="job.id"
                  :label="'Job' + job.id"
                  :value="job.id"
              />
            </el-select>
          </el-col>
          <el-col :span="8">
            <el-button @click="addJob" type="primary" size="small" style="width: 100%">Add</el-button>
          </el-col>
        </el-row>
      </el-card>
    </div>

    <!-- 中间面板 - 主要显示区域 -->
    <div class="middle-panel">
      <ElRow style="height: 100%">
        <ElCol :span="24">
          <div class="block">
            <el-image 
              :src="map_src" 
              style="max-width: 100%; max-height: 100%;" 
              fit="cover"
            >
              <template #placeholder>
                <div style="display: flex; justify-content: center; align-items: center; height: 100%; color: #999;">
                  加载中...
                </div>
              </template>
              <template #error>
                <div style="display: flex; justify-content: center; align-items: center; height: 100%; color: #f56c6c;">
                  图片加载失败
                </div>
              </template>
            </el-image>
          </div>
        </ElCol>
      </ElRow>

      <!-- <FactoryPlayerSSE :hide-control-panel="true" />

      <div class="floating-toolbar-wrapper">
        <div class="floating-toolbar">
          <div class="toolbar-left">
            <span class="toolbar-title">📦 包裹工厂管理</span>
            <span class="divider">|</span>
            <span class="toolbar-label">状态：{{ isRunningTest ? "运行中..." : "就绪" }}</span>
            <span class="divider">|</span>
            <span
              class="toolbar-label connection-status"
              :class="connectionStatus.scenario === '已连接' ? 'connected' : 'disconnected'"
            >
              包裹场景：{{ connectionStatus.scenario }}
            </span>
          </div>
          <div class="toolbar-right">
            <select v-model="selectedEnvironment" class="plan-select" :disabled="isRunningTest">
              <option value="simulation">仿真环境</option>
              <option value="real">真实现场环境</option>
            </select>
            <select v-model="selectedAlgorithm" class="plan-select" :disabled="isRunningTest">
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
      </div> -->


    

    </div>

    <!-- 右侧面板 - 日志与进度 -->
    <div class="right-side-panel">
      <!-- 配置上传区域 -->
      <div class="config-section">
        <div class="new-dag-font-style">Upload Config Set</div>
        <div class="upload-config-box">
          <el-card style="max-width: 100%; height: auto">
            <template #header>
              <div class="card-header">
                <el-tag @click="test" style="cursor: pointer">Config Set Operation</el-tag>
              </div>
            </template>
            <ElRow :gutter="10">
              <ElCol :span="8">
                <ElButton type="success" plain @click="getStandardConfig" style="width: 100%">
                  Get Standard
                </ElButton>
              </ElCol>
              <ElCol :span="8">
                <ElButton type="primary" plain @click="uploadConfigSet" style="width: 100%">
                  Upload
                </ElButton>
              </ElCol>
              <ElCol :span="8">
                <ElInput placeholder="Config Name!" v-model="config_name" size="small">
                </ElInput>
              </ElCol>
            </ElRow>
          </el-card>
          
          <el-upload
              ref="uploadRef"
              drag
              multiple
              :auto-upload="false"
              :on-change="handleChange"
              :file-list="fileList"
              :action="target_url"
              style="margin-top: 10px"
          >
            <el-icon class="el-icon--upload"><upload-filled/></el-icon>
            <div class="el-upload__text">Drop file here or <em>click to add!</em></div>
            <template #tip>
              <div class="el-upload__tip">A config set should contain 3 config files</div>
            </template>
          </el-upload>
        </div>
      </div>
      <!-- 自定义日志下载 -->
        <el-card style="margin-top: 15px">
          <template #header><span>Log Download</span></template>
          <el-row :gutter="8" class="mb-2">
            <el-col :span="12">
              <el-button @click="downloadLog('backend')" type="success" size="small" style="width: 100%">Backend Log</el-button>
            </el-col>
            <el-col :span="12">
              <el-button @click="downloadLog('system')" type="success" size="small" style="width: 100%">System Log</el-button>
            </el-col>
          </el-row>
        </el-card>

      <!-- 自定义 Job 进度 -->
        <el-card style="margin-top: 15px">
          <div style="font-size: 16px; font-weight: bold; margin-bottom: 10px">Job Process</div>
          <div v-for="job in jobProgressList" :key="job.id" style="margin-bottom: 15px">
            <div style="display: flex; justify-content: space-between; align-items: center;">
              <span>Job {{ job.id }}</span>
              <span v-if="job.status === 'FINISHED'" style="color: green;">Finished</span>
              <span v-else style="color: blue;">Processing...</span>
            </div>
            <el-progress :percentage="job.progress" :status="job.status === 'FINISHED' ? 'success' : undefined"/>
          </div>
        </el-card>
      </div>
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
import axios from "axios";

const store = useFactoryStore();
const monitorStore = useMonitorStore();

// ===== 原有状态 =====
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

// ===== 新增状态（来自旧版代码）=====
const uploadRef = ref();
const config_name = ref('');
const fileList = ref([]);
const target_url = ref('');
const map_src = ref("");
const fps = ref(1);
const factoryList = ref([]);
const selectedFactory = ref('');
const speedLevel = ref(parseInt(sessionStorage.getItem('speedLevel')) || 3);
const selectedAgv = ref(null);
const selectedMachine = ref(null);
const selectedJob = ref(null);
const jobProgressList = ref([]);

const agvList = ref([]);
const machineList = ref([]);
const jobList = ref([]);
const services = ref([]);

let agvIntervalId = null;
let machineIntervalId = null;
let jobIntervalId = null;
let intervalId = null;
let checkAliveInterval = null;
let progressInterval = null;

// Store 引用（保持兼容）
const stores = ref({
  factoryList: factoryList.value
});

// ===== 工具函数 =====
function updateMapSrcBuffered() {
  const preloadImg = new Image();
  const newSrc = `/api/map/update?_t=${Date.now()}`;

  preloadImg.onload = () => {
    map_src.value = newSrc;
  };
  preloadImg.src = newSrc;
}

// ===== 配置文件相关 =====
const handleChange = (uploadFile, uploadFiles) => {
  fileList.value.push(uploadFile);
  updateCurrentFactoryMapList();
};

const getStandardConfig = () => {
  fetch(`/api/standard/get?t=${Date.now()}`, { method: "GET" })
    .then(response => {
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status} ${response.statusText}`);
      }
      
      const disposition = response.headers.get('Content-Disposition');
      let filename = 'template_config_set.zip';

      if (disposition && disposition.includes('filename=')) {
        filename = disposition.split('filename=')[1].replace(/"/g, '');
      }

      return response.blob().then(blob => ({blob, filename}));
    })
    .then(({blob, filename}) => {
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
    })
    .catch(error => {
      ElMessage.error("Download failed");
      console.error(error);
    });
};

const uploadConfigSet = () => {
  target_url.value = '/api/' + config_name.value + `/yaml/upload?t=${Date.now()}`;
  uploadRef.value.submit();
  fileList.value = [];

  // ✅ 添加延迟，等待上传完成后刷新列表
  setTimeout(() => {
    updateCurrentFactoryMapList()
  }, 1000)
      
  ElMessage.success("Upload success!");
};

const test = () => {
  fetch("/api/test", {
    method: "POST",
    body: JSON.stringify({}),
  })
    .then((response) => {
      console.log(response);
    })
    .then((data) => {
      // ...
    })
    .catch((error) => {
      // ...
    });
};

// ===== 工厂列表更新 =====
const updateCurrentFactoryMapList = () => {
  fetch("/api/factory/list", {
    method: "GET",
  })
    .then((response) => {
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      return response.json();
    })
    .then((data) => {
      // 输出factory_list
      console.log(data.factory_list);
      stores.value.factoryList = data.factory_list;
      factoryList.value = data.factory_list;
    })
    .catch((error) => {
      console.error(error);
    });
};

// ===== 工厂渲染与控制 =====
const handleFactoryRender = () => {
  fetch("/api/map/render", {
    method: "POST",
    body: JSON.stringify({target_factory: selectedFactory.value}),
    headers: { "Content-Type": "application/json" },
  })
    .then((response) => {
      agvIntervalId = setInterval(loadAgvs, 1000);
      machineIntervalId = setInterval(loadMachines, 1000);
      jobIntervalId = setInterval(loadJobs, 1000);
      console.log(response);
    })
    .catch((error) => {
      console.error(error);
    });
};

const checkFactoryAlive = async () => {
  fetch("/api/factory/alive", { method: "GET" })
    .then((response) => {
      console.log(response);
      return response.json();
    })
    .then((data) => {
      console.log(data);
      if (data.is_alive) {
        agvIntervalId = setInterval(loadAgvs, 1000);
        machineIntervalId = setInterval(loadMachines, 1000);
        jobIntervalId = setInterval(loadJobs, 1000);
        intervalId = setInterval(updateMapSrcBuffered, 250);
        clearInterval(checkAliveInterval);
      }
    })
    .catch((error) => {
      console.error(error);
    });
};

function startCheckingFactory() {
  checkAliveInterval = setInterval(checkFactoryAlive, 500);
}

// ===== 数据加载函数 =====
const loadAgvs = async () => {
  const MAX_RETRIES = 1;
  const RETRY_DELAY = 2000;
  let retries = 0;

  while (retries < MAX_RETRIES) {
    try {
      const res = await axios.get(`/api/agvs?_t=${Date.now()}`);
      if (res.data && Array.isArray(res.data.agvs) && res.data.agvs.length > 0) {
        agvList.value = res.data.agvs;
        console.log('AGV data:', res.data.agvs);
        return;
      } else {
        retries++;
        console.warn(`Received empty AGV list (attempt ${retries}/${MAX_RETRIES})`);
        if (retries >= MAX_RETRIES) return;
        await new Promise(resolve => setTimeout(resolve, RETRY_DELAY));
      }
    } catch (error) {
      retries++;
      console.error(`Failed to load AGV (attempt ${retries}/${MAX_RETRIES}):`, error);
      if (retries >= MAX_RETRIES) return;
      await new Promise(resolve => setTimeout(resolve, RETRY_DELAY));
    }
  }
};

const loadMachines = async () => {
  const MAX_RETRIES = 1;
  const RETRY_DELAY = 2000;
  let retries = 0;

  while (retries < MAX_RETRIES) {
    try {
      const res = await axios.get(`/api/machines?_t=${Date.now()}`);
      if (res.data && Array.isArray(res.data.machines) && res.data.machines.length > 0) {
        machineList.value = res.data.machines;
        console.log('Machine data:', res.data.machines);
        return;
      } else {
        retries++;
        console.warn(`Received empty machine list (attempt ${retries}/${MAX_RETRIES})`);
        if (retries >= MAX_RETRIES) return;
        await new Promise(resolve => setTimeout(resolve, RETRY_DELAY));
      }
    } catch (error) {
      retries++;
      console.error(`Failed to load machine (attempt ${retries}/${MAX_RETRIES}):`, error);
      if (retries >= MAX_RETRIES) return;
      await new Promise(resolve => setTimeout(resolve, RETRY_DELAY));
    }
  }
};

const loadJobs = async () => {
  const MAX_RETRIES = 1;
  const RETRY_DELAY = 2000;
  let retries = 0;

  while (retries < MAX_RETRIES) {
    try {
      const res = await axios.get(`/api/jobs?_t=${Date.now()}`);
      if (res.data && Array.isArray(res.data.jobs) && res.data.jobs.length > 0) {
        jobList.value = res.data.jobs;
        console.log('Job data:', res.data.jobs);
        return;
      } else {
        retries++;
        console.warn(`Received empty or invalid job list (attempt ${retries}/${MAX_RETRIES})`);
        if (retries >= MAX_RETRIES) return;
        await new Promise(resolve => setTimeout(resolve, RETRY_DELAY));
      }
    } catch (error) {
      retries++;
      console.error(`Failed to load task (attempt ${retries}/${MAX_RETRIES}):`, error);
      if (retries >= MAX_RETRIES) return;
      await new Promise(resolve => setTimeout(resolve, RETRY_DELAY));
    }
  }
};

// ===== 工厂控制 API 调用 =====
const factoryStart = async () => {
  console.log("FactoryStart");
  try {
    const response = await axios.post('/api/factory/start');
    console.log('Response: ', response.data);
  } catch (error) {
    console.error('API request failed:', error.response ? error.response.data : error.message);
    throw error;
  }
};

const factoryPause = async () => {
  console.log("FactoryPause");
  try {
    const response = await axios.post('/api/factory/pause');
    console.log('Response: ', response.data);
  } catch (error) {
    console.error('API request failed:', error.response ? error.response.data : error.message);
    throw error;
  }
};

const factoryReset = async () => {
  console.log("FactoryReset");
  try {
    const response = await axios.post('/api/factory/reset');
    console.log('Response: ', response.data);
  } catch (error) {
    console.error('API request failed:', error.response ? error.response.data : error.message);
    throw error;
  }
};

const handleFactoryStart = () => {
  factoryStart();
};

const handleFactoryPause = () => {
  factoryPause();
};

const handleFactoryReset = () => {
  factoryReset();
};

// ===== 速度控制 =====
const changeSpeed = async (value) => {
  try {
    const res = await axios.post('/api/factory/speed', { speedLevel: value });
    sessionStorage.setItem('speedLevel', value);
    ElMessage.success(`Speed has been adjusted to ${value}`);
    console.log('Speed adjustment successful:', res.data);
  } catch (error) {
    console.error('Speed adjustment failed:', error);
    ElMessage.error('Speed adjustment failed');
  }
};

// ===== AGV 控制 =====
const pauseAgv = async () => {
  if (selectedAgv.value === null) {
    ElMessage.warning('Please Select AGV first');
    return;
  }
  try {
    await axios.post(`/api/agv/pause/${selectedAgv.value}`, { agvId: selectedAgv.value });
    ElMessage.success(`AGV ${selectedAgv.value} has been paused`);
  } catch (error) {
    console.error('Failed to pause AGV:', error);
    ElMessage.error('Failed to pause AGV');
  }
};

const resumeAgv = async () => {
  if (selectedAgv.value === null) {
    ElMessage.warning('Please Select AGV first');
    return;
  }
  try {
    await axios.post(`/api/agv/resume/${selectedAgv.value}`, { agvId: selectedAgv.value });
    ElMessage.success(`AGV ${selectedAgv.value} has been resumed`);
  } catch (error) {
    console.error('Failed to resume AGV:', error);
    ElMessage.error('Failed to resume AGV');
  }
};

// ===== Machine 控制 =====
const pauseMachine = async () => {
  if (selectedMachine.value === null) {
    ElMessage.warning('Please select a machine first');
    return;
  }
  try {
    await axios.post(`/api/machine/pause/${selectedMachine.value}`, { machineId: selectedMachine.value });
    ElMessage.success(`Machine ${selectedMachine.value} has been paused`);
  } catch (error) {
    console.error('Failed to pause machine:', error);
    ElMessage.error('Failed to pause machine');
  }
};

const resumeMachine = async () => {
  if (selectedMachine.value === null) {
    ElMessage.warning('Please select a machine first');
    return;
  }
  try {
    await axios.post(`/api/machine/resume/${selectedMachine.value}`, { machineId: selectedMachine.value });
    ElMessage.success(`Machine ${selectedMachine.value} has been resumed`);
  } catch (error) {
    console.error('Failed to resume machine:', error);
    ElMessage.error('Failed to resume machine');
  }
};

// ===== Job 控制 =====
const addJob = async () => {
  if (selectedJob.value === null) {
    ElMessage.warning('Please select a task first');
    return;
  }
  try {
    await axios.post(`/api/job/add/${selectedJob.value}`, { jobId: selectedJob.value });
    ElMessage.success(`Task ${selectedJob.value} has been added`);
  } catch (error) {
    console.error('Failed to add task:', error);
    ElMessage.error('Failed to add task');
  }
};

// ===== Job 进度获取 =====
const fetchJobProgress = async () => {
  try {
    const res = await fetch("/api/jobs/progress");
    if (!res.ok) {
      throw new Error("Failed to retrieve progress");
    }
    const data = await res.json();
    jobProgressList.value = data.jobs;
  } catch (error) {
    console.error("Failed to retrieve task progress:", error);
  }
};

// ===== 日志下载 =====
const downloadLog = (file_type) => {
  console.log(file_type);
  console.log("start download");
  fetch(`/api/log/download?t=${Date.now()}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({file_type: file_type}),
  })
    .then(response => {
      console.log(response);
      const disposition = response.headers.get('Content-Disposition');
      let filename = 'log.txt';

      if (disposition && disposition.includes('filename=')) {
        filename = disposition.split('filename=')[1].replace(/"/g, '');
      }

      return response.blob().then(blob => ({blob, filename}));
    })
    .then(({blob, filename}) => {
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
    })
    .catch(error => {
      ElMessage.error("Download failed");
      console.error(error);
    });
};

// ===== 执行方案 =====
const handleExecutePlan = async () => {
  if (isRunningTest.value) return;

  const environment = selectedEnvironment.value;
  const algorithm = selectedAlgorithm.value;

  console.log(`执行方案：环境=${environment}, 算法=${algorithm}`);

  if (environment === "real") {
    if (!connectionManager || !connectionManager.isScenarioConnected) {
      ElMessage.error("❌ 未连接到真实场景，无法执行实时调度");
      return;
    }

    try {
      isRunningTest.value = true;
      await connectionManager.executeControl("reset");
      ElMessage.success("✅ 已发送重置命令到后端");
      await connectionManager.executeControl("play", { algorithm });
      ElMessage.success(`✅ 已发送 ${algorithm === "default" ? "默认" : "优化"} 路由策略执行命令`);
    } catch (error) {
      ElMessage.error(`❌ 执行计划失败：${error.message}`);
    } finally {
      isRunningTest.value = false;
    }
  } else {
    isRunningTest.value = true;
    try {
      stopTest = runFullSystemTest(store, monitorStore, () => {
        isRunningTest.value = false;
        stopTest = null;
        ElMessage.success("✅ 仿真执行完成");
      });
    } catch (error) {
      isRunningTest.value = false;
      ElMessage.error(`仿真执行失败：${error.message}`);
    }
  }
};

// ===== 生命周期钩子 =====
onMounted(() => {
  // 包裹工厂初始化
  console.log("✅ PacketFactoryManage 已挂载");

  // 初始化多连接管理器
  const factoryId = store.selectedFactoryId;
  connectionManager = createFactoryConnectionManager(factoryId);

  connectionManager.init(
    {
      onStateUpdate: (data, eventType) => {
        console.log(`[PacketFactory] 状态更新 [${eventType}]:`, data);
        if (data.snapshot) {
          store.pushSnapshot(data.snapshot);
        }
      },
      onMetricsUpdate: (data, eventType) => {
        console.log(`[PacketFactory] 指标更新 [${eventType}]:`, data);
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
      state: ['packet_state', 'package_update', 'route_update'],
      metrics: ['packet_metrics', 'delivery_rate', 'route_efficiency'],
      control: ['packet_control', 'command_response'],
    }
  );

  updateConnectionStatus();

  // 旧版功能初始化
  updateCurrentFactoryMapList();
  startCheckingFactory();
  fetchJobProgress();
  
  progressInterval = setInterval(() => {
    fetchJobProgress();
  }, 1000);
});

const updateConnectionStatus = () => {
  if (connectionManager) {
    connectionStatus.value = connectionManager.getStatus();
  }
};

onUnmounted(() => {
  // 清理连接和测试
  console.log("🛑 PacketFactoryManage 卸载，清理连接和测试");
  if (stopTest) stopTest();
  if (eventSource) sseManager.disconnect(eventSource);
  if (connectionManager) connectionManager.disconnect();
  
  // 清理旧版定时器
  clearInterval(agvIntervalId);
  clearInterval(machineIntervalId);
  clearInterval(jobIntervalId);
  clearInterval(intervalId);
  clearInterval(checkAliveInterval);
  clearInterval(progressInterval);
});
</script>

<style scoped>
@import "../styles/FactoryManage.css";

/* 新增样式 */
.config-section {
  margin-bottom: 15px;
}

.upload-config-box {
  padding: 10px;
  background-color: #f0f8ff;
  border-radius: 12px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
}

.factory-info-section {
  margin-top: 15px;
  padding: 10px;
  background: #f5f7fa;
  border-radius: 8px;
}

.new-dag-font-style {
  font-size: 16px;
  margin-bottom: 15px;
  font-weight: bold;
}

.svc-container {
  display: flex;
  flex-wrap: wrap;
  padding: 10px;
  list-style-type: none;
  gap: 8px;
}

.svc-item {
  display: inline-block;
  margin: 2px;
  padding: 2px;
  border-radius: 12px;
}

.vue-flow__node-input {
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  background: #ffffff;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
  transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
  width: auto;
  padding: 10px;
  font-size: 14px;
  cursor: grab;
}

.vue-flow__node-input:hover {
  border-color: #94a3b8;
  box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
}

.description {
  white-space: pre-wrap;
  word-wrap: break-word;
  max-width: 300px;
}

.mb-2 {
  margin-bottom: 10px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.el-upload__tip {
  font-size: 12px;
  color: #666;
}

/* 确保容器使用 flex 布局 */
.factory-manage-container {
  display: flex;
  height: 100vh;
  overflow: hidden;
  width: 100%;
}

/* 左侧面板 - 整体滚动 */
.left-panel {
  flex: 0 0 auto;
  width: 280px;
  height: 100%;
  overflow-y: auto;
  overflow-x: hidden;
  padding: 10px;
  box-sizing: border-box;
  padding-bottom: 50px; /* 增加底部内边距，确保最后一个元素完整显示 */
  scroll-padding-bottom: 50px; /* 滚动时底部预留空间 */
}

/* 右侧面板 - 整体滚动 */
.right-side-panel {
  flex: 0 0 auto;
  height: 100%;
  overflow-y: auto;
  overflow-x: hidden;
  padding: 10px;
  box-sizing: border-box;
  padding-bottom: 50px; /* 增加底部内边距，确保最后一个元素完整显示 */
  scroll-padding-bottom: 50px; /* 滚动时底部预留空间 */
}

/* 中间面板 - 保持固定高度 */
.middle-panel {
  flex: 1;
  height: 100%;
  overflow: hidden;
  padding: 10px;
  box-sizing: border-box;
}

/* 滚动条样式优化 */
.left-panel::-webkit-scrollbar,
.right-side-panel::-webkit-scrollbar {
  width: 6px;
}

.left-panel::-webkit-scrollbar-thumb,
.right-side-panel::-webkit-scrollbar-thumb {
  background-color: #ccc;
  border-radius: 3px;
}

.left-panel::-webkit-scrollbar-thumb:hover,
.right-side-panel::-webkit-scrollbar-thumb:hover {
  background-color: #999;
}

/* 确保最后一个卡片有足够间距 */
.left-panel > .el-card:last-child,
.right-side-panel > .el-card:last-child {
  margin-bottom: 20px;
}

</style>
