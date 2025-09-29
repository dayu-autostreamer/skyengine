<template>
  <div class="outline">
    <div>
      <h3>Factory Management</h3>
    </div>

    <div>
      <div class="new-dag-font-style">Upload Config Set</div>
      <div class="upload-config-box">
        <ElRow>
          <ElCol :span="8">
            <el-card style="max-width: 550px;height: 180px">
              <template #header>
                <div class="card-header">
                  <el-tag @click="test">Config Set Operation</el-tag>
                </div>
              </template>
              <ElRow>
                <ElCol :span="11">
                  <ElButton type="success" plain @click="getStandardConfig">
                    Get Standard
                  </ElButton>
                </ElCol>
                <ElCol :span="5">
                  <ElButton type="primary" plain @click="uploadConfigSet">
                    Upload
                  </ElButton>
                </ElCol>
                <ElCol :span="8">
                  <ElInput placeholder="Set Config Name!" v-model="config_name">
                  </ElInput>
                </ElCol>
              </ElRow>
            </el-card>
          </ElCol>
          <ElCol :span="1">

          </ElCol>
          <ElCol :span="15">
            <el-upload
                ref="uploadRef"
                drag
                multiple
                :auto-upload="false"
                :on-change="handleChange"
                :file-list="fileList"
                :action="target_url"
            >
              <el-icon class="el-icon--upload">
                <upload-filled/>
              </el-icon>
              <div class="el-upload__text">
                Drop file here or <em>click to add !</em>
              </div>
              <template #tip>
                <div class="el-upload__tip">
                  A config set should contain 3 config files
                </div>
              </template>
            </el-upload>
          </ElCol>


        </ElRow>

      </div>


      <br/>
      <br/>
      <div style="display: inline">
        <div class="new-dag-font-style">
          Factory Info
          <el-tooltip placement="right">
            <template #content>
              Both logical and physical included.
            </template>
            <el-button size="small" circle>i</el-button>
          </el-tooltip>
        </div>
      </div>

      <div>
        <ul style="list-style-type: none" class="svc-container">
          <li
              v-for="(service, index) in services"
              :key="index"
              class="svc-item"
          >
            <el-tooltip
                placement="right"
                :open-delay="500"
                enterable
            >
              <template #content>
                <div class="description">
                  {{ service.description }}
                </div>
              </template>
              <div
                  class="vue-flow__node-input"
                  :draggable="true"
                  @dragstart="onDragStart($event, '', service)"
              >
                {{ service.name }}
              </div>
            </el-tooltip>
          </li>
        </ul>
      </div>
    </div>
    <br/>

    <!-- 绘制区域,自动绘制 -->
    <div>
      <ElRow>
        <el-col :span="6">
          <el-card style="max-width: 480px">
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


          <el-card class="mt-3" style="max-width: 480px">
            <template #header>
              <span>AGV Control</span>
            </template>
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
                  <el-button @click="pauseAgv" type="warning" size="small">Pause</el-button>
                  <el-button @click="resumeAgv" type="success" size="small">Go</el-button>
                </el-button-group>
              </el-col>
            </el-row>
          </el-card>

          <el-card class="mt-3" style="max-width: 480px">
            <template #header>
              <span>Machine Control</span>
            </template>
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
                  <el-button @click="pauseMachine" type="warning" size="small">Pause</el-button>
                  <el-button @click="resumeMachine" type="success" size="small">Go</el-button>
                </el-button-group>
              </el-col>
            </el-row>
          </el-card>

          <el-card class="mt-3" style="max-width: 480px">
            <template #header>
              <span>Job Control</span>
            </template>
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

          <el-card class="mt-3" style="max-width: 480px">
            <template #header>
              <span>Log Download</span>
            </template>
            <el-row :gutter="8" class="mb-2">
              <el-col :span="8">

              </el-col>
              <el-col :span="8">
                <el-button @click="downloadLog('backend')" type="success" size="small" style="width: 100%">Backend Log
                </el-button>
              </el-col>
              <el-col :span="8">
                <el-button @click="downloadLog('system')" type="success" size="small" style="width: 100%">System Log
                </el-button>
              </el-col>
            </el-row>
          </el-card>


<el-card style="max-width: 480px; margin-top: 10px">
  <div style="font-size: 16px; font-weight: bold; margin-bottom: 10px">
    Job Pools
  </div>

  <!-- 绑定 v-model，控制展开的项 -->
  <el-collapse>
    <!-- 遍历 jobDict 的每个分组 -->
    <el-collapse-item
      v-for="(jobs, jobId) in jobDict"
      :key="jobId"
      :name="jobId"
    >
      <!-- 折叠面板标题 -->
      <template #title>
        <span style="font-size: 15px; font-weight: bold;">
          Job Pool {{ jobId }}
        </span>
      </template>

      <!-- 折叠内容：当前分组下的 jobs -->
      <div v-for="job in jobs" :key="job.id" style="margin-bottom: 12px;">
        <div style="display: flex; justify-content: space-between; align-items: center;">
          <span>Job {{ job.id }}</span>
          <span v-if="job.status === 'FINISHED'" style="color: green;">Finished</span>
          <span v-else style="color: blue;">Processing...</span>
        </div>
        <el-progress
          :percentage="job.progress"
          :status="job.status === 'FINISHED' ? 'success' : undefined"
        />
      </div>
    </el-collapse-item>
  </el-collapse>
</el-card>
        </el-col>

        <ElCol :span="2"></ElCol>

        <ElCol :span="16">
          <el-card>
            <template #header>
              <ElRow>
                <ElCol :span="16">
                  <span style="font-weight: bolder;font-size: 20px">Current Factory Map</span>
                </ElCol>
                <ElCol :span="8">
                  <ElButton type="success" plain @click="updateAgent">
                    Agent选择
                  </ElButton>
                  <ElSelect v-model="selectedAgent" placeholder="请选择Agent" style="width: 200px">
                    <ElOption
                        v-for="item in agentList"
                        :key="item.value"
                        :label="item.label"
                        :value="item.value"
                    />
                  </ElSelect>
                </ElCol>
              </ElRow>

            </template>
            <div class="block">
              <el-image :src="map_src" style="max-width: 100%; max-height: 100%;" fit="cover">
              </el-image>
            </div>

          </el-card>


        </ElCol>

      </ElRow>
    </div>
    <br/>
    <br/>
  </div>
</template>

<script>
import {
  ElButton, ElCol, ElInput, ElMessage, ElRow, ElTable, ElTableColumn, ElTag, ElTooltip, ElImage,
} from "element-plus";

import {nextTick, ref, onMounted, onUnmounted} from "vue";
import {Connection, Link, MagicStick, Right, Picture as IconPicture} from '@element-plus/icons-vue';
import {UploadFilled} from '@element-plus/icons-vue'
import axios from "axios";
import {useFactoryState} from "/@/stores/factoryState.ts"

export default {
  name: "FactoryManage",
  components: {
    nextTick,
    ElTable,
    ElImage,
    ElTableColumn,
    ElTooltip,
    ElTag,
    ElInput,
    ElButton,
    ElCol,
    ElRow,
    ElMessage,
    Connection,
    Link,
    Right,
    MagicStick,
    UploadFilled,
    IconPicture
  },
  setup() {
    const uploadRef = ref();
    const config_name = ref('');
    const fileList = ref([]);
    const target_url = ref('');
    const map_src = ref("");
    const fps = ref(1);
    const factoryList = ref([]);
    const selectedFactory = ref('');
    let agvIntervalId = null;
    let machineIntervalId = null;
    let jobIntervalId = null;
    let intervalId = null;
    const stores = useFactoryState()


    // ---------- 智能体相关流程 ----------
    const selectedAgent = ref("") //系统开始时会返回当前init Agent
    const agentList = ref([
      {value: "agent1", label: "智能Agent 1"},
      {value: "agent2", label: "智能Agent 2"},
      {value: "agent3", label: "智能Agent 3"},
    ])

    const updateAgent = () => {
      const data = {
        'agent': selectedAgent.value
      }
      fetch("/api/agent/update", {
        method: "POST",
        body: JSON.stringify(data),
      }).then((response) => {
            if (!response.ok) {
              throw new Error(`HTTP error! status: ${response.status}`);
            }
            return response.json();
          }
      )
          .then((data) => {
            console.log(data)
          })
          .catch((error) => {
          });
    }

    const agvList = ref([]);
    const machineList = ref([]);
    const jobList = ref([]);

    let checkAliveInterval = null; // 用于持续检查 factory/alive 的定时器

    function updateMapSrcBuffered() {
      const preloadImg = new Image();
      const newSrc = `/api/map/update?_t=${Date.now()}`;

      preloadImg.onload = () => {
        map_src.value = newSrc; // 图片加载完后再替换
      };
      preloadImg.src = newSrc;
    }

    onMounted(() => {
      updateCurrentFactoryMapList()
    });
    onUnmounted(() => {
      clearInterval(agvIntervalId);
      clearInterval(machineIntervalId);
      clearInterval(jobIntervalId);
      clearInterval(intervalId);
      clearInterval(checkAliveInterval);
    });

    const handleChange = (uploadFile, uploadFiles) => {
      fileList.value.push(uploadFile)
      updateCurrentFactoryMapList()
    }
    const getStandardConfig = () => {
      fetch(`/api/standard/get?t=${Date.now()}`, {
        method: "GET"
      })
          .then(response => {
            if (!response.ok) {
              throw new Error(`HTTP error! status: ${response.status} ${response.statusText}`);
            }

            // 从响应头获取 filename
            const disposition = response.headers.get('Content-Disposition');
            let filename = 'template_config_set.zip';  // 默认

            if (disposition && disposition.includes('filename=')) {
              filename = disposition.split('filename=')[1].replace(/"/g, '');
            }

            return response.blob().then(blob => ({blob, filename}));
          })
          .then(({blob, filename}) => {
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = filename;  // 动态指定 filename
            document.body.appendChild(a);
            a.click();
            a.remove();
            window.URL.revokeObjectURL(url);
          })
          .catch(error => {
            ElMessage.error("Download failed");
            console.error(error);
          });
    }

    const uploadConfigSet = () => {
      target_url.value = '/api/' + config_name.value + `/yaml/upload?t=${Date.now()}`
      uploadRef.value.submit()
      fileList.value = []
      ElMessage.success("Upload success!");
    }


    const test = () => {
      fetch("/api/test", {
        method: "POST",
        body: JSON.stringify({}),
      })
          .then((response) => {
            console.log(response)
          })
          .then((data) => {

          })
          .catch((error) => {
          });
    }

    const updateCurrentFactoryMapList = () => {
      fetch("/api/factory/list", {
        method: "GET",
      }).then((response) => {
            if (!response.ok) {
              throw new Error(`HTTP error! status: ${response.status}`);
            }
            return response.json();
          }
      )
          .then((data) => {
            stores.factoryList = data.factory_list;
          })
          .catch((error) => {
          });
    }


    const handleFactoryRender = () => {
      fetch("/api/map/render", {
        method: "POST",
        body: JSON.stringify({target_factory: selectedFactory.value}),
      })
          .then((response) => {
            agvIntervalId = setInterval(loadAgvs(), 1000);
            machineIntervalId = setInterval(loadMachines(), 1000);
            jobIntervalId = setInterval(loadJobs(), 1000);
            console.log(response);
          })
          .catch((error) => {
          });
    }

    // 测试factory是否alive，若alive则更新下拉菜单和图片
    const checkFactoryAlive = async () => {
      fetch("/api/factory/alive", {
        method: "GET",
      })
          .then((response) => {
            console.log(response)
            return response.json();
          })
          .then((data) => {
            console.log(data);
            if (data.is_alive) {
              agvIntervalId = setInterval(loadAgvs(), 1000);
              machineIntervalId = setInterval(loadMachines(), 1000);
              jobIntervalId = setInterval(loadJobs(), 1000);

              // 启动成功,则每隔 0.2 秒更新一次图片
              intervalId = setInterval(updateMapSrcBuffered, 250);

              clearInterval(checkAliveInterval);
            }
          })
          .catch((error) => {
            console.log(error);
          });
    };

    // 启动持续检查：每 1 秒检查一次，直到启动成功
    function startCheckingFactory() {
      // 每 500ms 检查一次（不要太频繁，避免压垮服务器）
      checkAliveInterval = setInterval(checkFactoryAlive, 500);
    }

    // 启动整个检查流程
    startCheckingFactory();

    const downloadLog = (file_type) => {
      console.log(file_type)
      console.log("start download")
      fetch(`/api/log/download?t=${Date.now()}`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({file_type: file_type}),
      })
          .then(response => {
            console.log(response)
            // 从响应头获取 filename
            const disposition = response.headers.get('Content-Disposition');
            let filename = 'log.txt';  // 默认

            if (disposition && disposition.includes('filename=')) {
              filename = disposition.split('filename=')[1].replace(/"/g, '');
            }

            return response.blob().then(blob => ({blob, filename}));
          })
          .then(({blob, filename}) => {
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = filename;  // 动态指定 filename
            document.body.appendChild(a);
            a.click();
            a.remove();
            window.URL.revokeObjectURL(url);
          })
          .catch(error => {
            ElMessage.error("Download failed");
            console.error(error);
          });

    }

    const factoryStart = async () => {
      console.log("FactoryStart")
      try {
        const response = await axios.post('/api/factory/start');
        console.log('Response: ', response.data);
      } catch (error) {
        console.error('API request failed:', error.response ? error.response.data : error.message);
        throw error;
      }
    }

    const factoryPause = async () => {
      console.log("FactoryPause")
      try {
        const response = await axios.post('/api/factory/pause');
        console.log('Response: ', response.data);
      } catch (error) {
        console.error('API request failed:', error.response ? error.response.data : error.message);
        throw error;
      }
    }

    const factoryReset = async () => {
      console.log("FactoryReset")
      try {
        const response = await axios.post('/api/factory/reset');
        console.log('Response: ', response.data);
      } catch (error) {
        console.error('API request failed:', error.response ? error.response.data : error.message);
        throw error;
      }
    }

    const loadAgvs = async () => {
      const MAX_RETRIES = 1;
      const RETRY_DELAY = 2000;

      let retries = 0;

      while (retries < MAX_RETRIES) {
        try {
          const res = await axios.get(`/api/agvs?_t=${Date.now()}`);

          agvList.value = res.data.agvs;
          console.log('AGV data:', res.data.agvs);

          // 检查是否成功获取数据且 agvs 存在
          if (res.data && Array.isArray(res.data.agvs) && res.data.agvs.length > 0) {
            agvList.value = res.data.agvs;
            console.log('AGV data:', res.data.agvs);
            return; // 成功获取非空数据，退出
          } else {
            // 数据为空，视为需要重试的情况
            retries++;
            console.warn(`Received empty AGV list (attempt ${retries}/${MAX_RETRIES})`);

            if (retries >= MAX_RETRIES) {
              // ElMessage.warning('Loaded AGV list is empty after multiple attempts');
              return;
            }

            // 等待后重试
            await new Promise(resolve => setTimeout(resolve, RETRY_DELAY));
          }
        } catch (error) {
          retries++;
          console.error(`Failed to load AGV (attempt ${retries}/${MAX_RETRIES}):`, error);

          if (retries >= MAX_RETRIES) {
            // ElMessage.error('Failed to load AGV list after multiple attempts');
            return;
          }

          // 等待后重试
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

          // 判断是否成功获取非空的 machines 数据
          if (res.data && Array.isArray(res.data.machines) && res.data.machines.length > 0) {
            machineList.value = res.data.machines;
            console.log('Machine data:', res.data.machines);
            return; // 成功获取有效数据，退出
          } else {
            // 返回数据格式正确但 machines 为空数组
            retries++;
            console.warn(`Received empty machine list (attempt ${retries}/${MAX_RETRIES})`);

            if (retries >= MAX_RETRIES) {
              // ElMessage.warning('Loaded machine list is empty after multiple attempts');
              return;
            }

            // 等待后重试
            await new Promise(resolve => setTimeout(resolve, RETRY_DELAY));
          }
        } catch (error) {
          retries++;
          console.error(`Failed to load machine (attempt ${retries}/${MAX_RETRIES}):`, error);

          if (retries >= MAX_RETRIES) {
            // ElMessage.error('Failed to load machine list after multiple attempts');
            return;
          }

          // 等待后重试
          await new Promise(resolve => setTimeout(resolve, RETRY_DELAY));
        }
      }
    };

    const loadJobs = async () => {
      const MAX_RETRIES = 1;
      const RETRY_DELAY = 2000;

      // 如果没有缓存或解析失败，则从服务器获取
      let retries = 0;
      while (retries < MAX_RETRIES) {
        try {
          const res = await axios.get(`/api/jobs?_t=${Date.now()}`);

          // 检查响应数据是否存在且 jobs 是非空数组
          if (res.data && Array.isArray(res.data.jobs) && res.data.jobs.length > 0) {
            jobList.value = res.data.jobs;
            console.log('Job data:', res.data.jobs);

            return; // 成功获取非空数据，退出重试循环
          } else {
            // 数据为空或格式不符合预期（如 jobs 不存在或非数组）
            retries++;
            console.warn(`Received empty or invalid job list (attempt ${retries}/${MAX_RETRIES})`);

            if (retries >= MAX_RETRIES) {
              // ElMessage.warning('Loaded job list is empty or invalid after multiple attempts');
              return;
            }

            // 等待后重试
            await new Promise(resolve => setTimeout(resolve, RETRY_DELAY));
          }
        } catch (error) {
          retries++;
          console.error(`Failed to load task (attempt ${retries}/${MAX_RETRIES}):`, error);

          if (retries >= MAX_RETRIES) {
            // ElMessage.error('Failed to load task list after multiple attempts');
            return;
          }

          // 等待后重试
          await new Promise(resolve => setTimeout(resolve, RETRY_DELAY));
        }
      }
    };

    return {
      uploadConfigSet,
      getStandardConfig,
      handleChange,
      handleFactoryRender,
      uploadRef,
      test,
      config_name,
      target_url,
      factoryStart,
      factoryPause,
      factoryReset,
      agvList,
      machineList,
      jobList,
      downloadLog,
      map_src,
      fps,
      factoryList,
      selectedFactory,
      stores,
      agentList,
      selectedAgent,
      updateAgent
    };
  },

  data() {
    return {
      speedLevel: parseInt(sessionStorage.getItem('speedLevel')) || 3,
      selectedAgv: null,
      selectedMachine: null,
      selectedJob: null,

      jobProgressList: [],
      jobDict: {},

      progressInterval: null, // 用于保存定时器引用
    };
  },

  methods: {
    handleFactoryStart() {
      this.factoryStart();
    },

    handleFactoryPause() {
      this.factoryPause();
    },

    handleFactoryReset() {
      this.factoryReset();
    },

    async changeSpeed(value) {
      try {
        const res = await axios.post('/api/factory/speed', {
          speedLevel: value
        });
        sessionStorage.setItem('speedLevel', value);
        this.$message.success(`Speed has been adjusted to ${value}`);
        console.log('Speed adjustment successful:', res.data);
      } catch (error) {
        console.error('Speed adjustment failed:', error);
        this.$message.error('Speed adjustment failed');
      }
    },

    async pauseAgv() {
      if (this.selectedAgv === null) {
        this.$message.warning('Please Select AGV first');
        return;
      }
      try {
        await axios.post(`/api/agv/pause/${this.selectedAgv}`, {
          agvId: this.selectedAgv
        });
        this.$message.success(`AGV ${this.selectedAgv} has been paused`);
      } catch (error) {
        console.error('Failed to pause AGV:', error);
        this.$message.error('Failed to pause AGV');
      }
    },

    async resumeAgv() {
      if (this.selectedAgv === null) {
        this.$message.warning('Please Select AGV first');
        return;
      }
      try {
        await axios.post(`/api/agv/resume/${this.selectedAgv}`, {
          agvId: this.selectedAgv
        });
        this.$message.success(`AGV ${this.selectedAgv} has been resumed`);
      } catch (error) {
        console.error('Failed to resume AGV:', error);
        this.$message.error('Failed to resume AGV');
      }
    },

    async pauseMachine() {
      if (this.selectedMachine === null) {
        this.$message.warning('Please select a machine first');
        return;
      }
      try {
        await axios.post(`/api/machine/pause/${this.selectedMachine}`, {
          machineId: this.selectedMachine
        });
        this.$message.success(`Machine ${this.selectedMachine} has been paused`);
      } catch (error) {
        console.error('Failed to pause machine:', error);
        this.$message.error('Failed to pause machine');
      }
    },

    async resumeMachine() {
      if (this.selectedMachine === null) {
        this.$message.warning('Please select a machine first');
        return;
      }
      try {
        await axios.post(`/api/machine/resume/${this.selectedMachine}`, {
          machineId: this.selectedMachine
        });
        this.$message.success(`Machine ${this.selectedMachine} has been resumed`);
      } catch (error) {
        console.error('Failed to resume machine:', error);
        this.$message.error('Failed to resume machine');
      }
    },

    async addJob() {
      if (this.selectedJob === null) {
        this.$message.warning('Please select a task first');
        return;
      }
      try {
        await axios.post(`/api/job/add/${this.selectedJob}`, {
          jobId: this.selectedJob
        });
        this.$message.success(`Task ${this.selectedJob} has been added`);
      } catch (error) {
        console.error('Failed to add task:', error);
        this.$message.error('Failed to add task');
      }
    },

    async fetchJobProgress() {
      try {
        const res = await fetch("/api/jobs/progress");
        if (!res.ok) {
          throw new Error("Failed to retrieve progress");
        }
        const data = await res.json();
        this.jobProgressList = data.jobs;
        // 根据 id 分组
        this.jobDict = {};
        for (const job of data.jobs) {
          const key = String(job.id);
          if (!this.jobDict[key]) {
            this.jobDict[key] = [];
          }
          this.jobDict[key].push(job);
        }
      } catch (error) {
        console.error("Failed to retrieve task progress:", error);
      }
    }
  }
  ,
  mounted() {
    this.fetchJobProgress(); // 首次加载
    this.progressInterval = setInterval(() => {
      this.fetchJobProgress();
    }, 1000); // 每 1 秒刷新一次
  }
  ,
}
;
</script>

<style scoped>
.block {
  background-color: #f0f8ff; /* 浅蓝背景 */
  padding: 10px;
  border: 1px solid #ddd;
  min-height: 400px; /* 最小高度可以按需调整 */
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 12px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
}

.upload-config-box {
  padding: 20px;
  background-color: #f0f8ff; /* 浅蓝背景 */
  border-radius: 12px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
  margin: 0 auto;
}

body {
  font-family: Arial, sans-serif;
  background-color: #f9f9f9;
  margin: 0;
  display: flex;
  justify-content: center;
  align-items: center;
  height: 100vh;
}

form {
  max-width: 600px;
  padding: 20px;
  background-color: #fff;
  border-radius: 8px;
  /* box-shadow: 0px 4px 6px rgba(0, 0, 0, 0.1); */
}

h3 {
  font-size: 24px;
  color: #333;
  margin-bottom: 20px;
}

input[type="text"],
input[type="file"] {
  width: calc(100% - 20px);
  padding: 10px;
  margin-bottom: 10px;
  border: 1px solid #ccc;
  border-radius: 4px;
  font-size: 16px;
}

input[type="file"] {
  cursor: pointer;
}

.draw-container {
  width: 100%;
  height: 500px;

  display: flex;
  align-items: flex-start;
  justify-content: center;
  margin-top: 15px;
  border: 1px solid #ccc;
}

.compact-container {
  width: 100%;
  height: 100px;
}

.el-button {
  font-size: 16px;
  margin-right: 10px;
}

.el-button:first-child {
  margin-left: 0;
}

.outline {
  /* max-width: 600px; */
  padding: 20px;
  background-color: #fff;
  border-radius: 8px;
  /* box-shadow: 0px 4px 6px rgba(0, 0, 0, 0.1); */
}

.new-dag-font-style {
  font-size: 16px;
  margin-bottom: 15px;
  font-weight: bold;
}

.svc-container {
  margin-top: -20px;
  display: flex;
  flex-wrap: wrap;
  padding: 10px;
  list-style-type: none;
}


.svc-item {
  display: inline-block;
  margin: 2px;
  padding: 2px;
  border-radius: 12px;
}

.vue-flow__node-input {
  border: 1px solid #e2e8f0; /* 柔和的蓝灰色 */
  border-radius: 8px;
  background: #ffffff;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
  transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
  width: auto;
  padding: 10px;
  font-size: 18px;
}

.vue-flow__node-input:hover {
  border-color: #94a3b8; /* 悬停时稍深的颜色 */
  box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
}

.vue-flow__node-input2 {
  width: auto;
  padding: 5px;
  font-size: 20px;
}

.description {
  white-space: pre-wrap;
  word-wrap: break-word;
}

.el-button {
  font-size: 16px;
  margin-right: 10px;
}

.el-button:first-child {
  margin-left: 0;
}

.process-panel,
.layout-panel {
  display: flex;
  gap: 10px;
}

.process-panel {
  background-color: #2d3748;
  padding: 10px;
  border-radius: 8px;
  box-shadow: 0 0 10px rgba(0, 0, 0, 0.5);
  display: flex;
  flex-direction: column;
}

.process-panel button {
  border: none;
  cursor: pointer;
  background-color: #4a5568;
  border-radius: 8px;
  color: white;
  box-shadow: 0 0 10px rgba(0, 0, 0, 0.5);
}

.process-panel button {
  font-size: 16px;
  width: 40px;
  height: 40px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.checkbox-panel {
  display: flex;
  align-items: center;
  gap: 10px;
}

.process-panel button:hover,
.layout-panel button:hover {
  background-color: #2563eb;
  transition: background-color 0.2s;
}

.process-panel label {
  color: white;
  font-size: 12px;
}

.drag-tip {
  position: absolute;
  top: 20px;
  left: 50%;
  transform: translateX(-50%);
  z-index: 10;
  background: rgba(255, 255, 255, 0.9);
  padding: 8px 16px;
  border-radius: 24px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.1);
  display: flex;
  align-items: center;
  gap: 8px;
  backdrop-filter: blur(4px);
  border: 1px solid #ebeef5;
  animation: float 3s ease-in-out infinite;
}

.tip-icon {
  color: #409eff;
  font-size: 18px;
}

.drag-tip span {
  font-family: 'Segoe UI', system-ui, sans-serif;
  font-size: 14px;
  color: #606266;
  font-weight: 500;
  letter-spacing: 0.3px;
}

@keyframes float {
  0%, 100% {
    transform: translateX(-50%) translateY(0);
  }
  50% {
    transform: translateX(-50%) translateY(-4px);
  }
}


.dag-preview {
  position: relative;
  padding: 8px;
  border-radius: 8px;
  background: #f8fafc;
  transition: all 0.3s;
}

.mini-dag {
  display: flex;
  align-items: center;
  gap: 4px;
  margin-bottom: 8px;

  .node {
    padding: 2px 8px;
    background: #e2e8f0;
    border-radius: 4px;
    font-size: 12px;
  }

  .edges {
    color: #94a3b8;
    display: flex;
    gap: 2px;
  }
}

.stats {
  display: flex;
  gap: 8px;

  .el-tag {
    display: flex;
    align-items: center;
    gap: 4px;
  }
}


.dag-detail-card {
  position: fixed;
  z-index: 99999 !important;
  pointer-events: none;
  width: 400px;
  height: 300px;
  right: 120px;
  left: auto !important;
  top: 40% !important;
  transform: translate(-20px, -50%) !important;
  background: white;
  border-radius: 12px;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.1);
  padding: 16px;
  animation: slide-in 0.3s ease;
  max-width: 90vw;
  max-height: 80vh;
  overflow: auto;
  transition: all 0.3s ease;

  .dag-title {
    font-weight: 600;
    margin-bottom: 12px;
    color: #2d3748;
  }


}

@keyframes slide-in {
  from {
    opacity: 0;
    transform: translateY(8px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.dag-detail-card .vue-flow__node {
  padding: 8px 12px;
  border-radius: 6px;
  font-size: 14px;
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.1);
}

.dag-detail-card .vue-flow__edge-path {
  stroke: #64748b;
  stroke-width: 2;
}

.mini-dag .node {
  max-width: 80px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.edges {
  .no-edges {
    color: #999;
    font-size: 12px;
  }

  .el-icon {
    &:nth-child(n+4) {
      display: none;
    }
  }
}

.el-table__body tr.hover-row > td {
  z-index: auto !important;
}

.first-service {
  background: #e2e8f0;
  border-radius: 4px;
  padding: 2px 8px;
  font-size: 12px;
  max-width: 120px;
  overflow: hidden;
  text-overflow: ellipsis;
}

.main-flow .vue-flow__node {
}

.preview-flow {
  z-index: 100000;
  pointer-events: none;
}

.preview-flow .vue-flow__node {
  transform: scale(0.8);
  cursor: default !important;
}

</style>
