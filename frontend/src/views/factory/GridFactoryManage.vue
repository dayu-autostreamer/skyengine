<template>
  <div class="outline">
    <div>
      <h3>GridFactory Management</h3>
    </div>
    <!--  上传区域,动态配置  -->
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

    <!-- 展示控制区域,展示运行系统 -->
    <div class="factory-container">
      <el-row :gutter="20">
        <!-- 左侧控制面板 -->
        <el-col :span="6">
          <!-- Control Panel -->
          <el-card class="panel-card" shadow="hover">
            <div class="panel-header">
              <span>Control Panel</span>
            </div>

            <el-form label-position="top" class="control-form">
              <el-form-item label="选择工厂">
                <el-select v-model="selectedFactory" placeholder="Select Factory">
                  <el-option
                      v-for="factory in stores.factoryList"
                      :key="factory.id"
                      :label="'Factory: ' + factory.id"
                      :value="factory.id"
                  />
                </el-select>
              </el-form-item>
              <el-form-item label="选择任务集">
                <el-select v-model="selectedJob" placeholder="Select Job">
                  <el-option
                      v-for="job in stores.jobList"
                      :key="job.id"
                      :label="'Job: ' + job.id"
                      :value="job.id"
                  />
                </el-select>
              </el-form-item>
              <el-form-item label="操作">
                <el-row :gutter="8">
                  <el-col :span="5">
                    <el-button type="primary" @click="factoryRender" style="width: 100%">Render</el-button>
                  </el-col>
                  <el-col :span="5">
                    <el-button type="success" @click="factoryStart" style="width: 100%">Start</el-button>
                  </el-col>
                  <el-col :span="5">
                    <el-button type="warning" @click="factoryPause" style="width: 100%">Pause</el-button>
                  </el-col>
                  <el-col :span="5">
                    <el-button type="warning" @click="factoryResume" style="width: 100%">Resume</el-button>
                  </el-col>
                  <el-col :span="4">
                    <el-button type="danger" @click="factoryReset" style="width: 100%">Reset</el-button>
                  </el-col>

                </el-row>
              </el-form-item>

              <el-form-item label="Speed Level">
                <el-slider v-model="speedLevel" :min="1" :max="10" show-input @change="changeSpeed"/>
              </el-form-item>
            </el-form>
          </el-card>

          <!-- Agent Control -->
          <el-card class="panel-card mt-3" shadow="hover">
            <div class="panel-header">
              <span>Agent Control</span>
            </div>
            <el-form label-position="top" class="control-form">
              <el-form-item label="AGV Agent">
                <el-col :span="16">
                  <el-select v-model="selectedAgvAgent" placeholder="Select AGV Agent" style="width: 100%">
                    <el-option
                        v-for="agv_agent in agvAgentList"
                        :key="agv_agent.id"
                        :label="' AgvAgent' + job.id"
                        :value="agv_agent.id"
                    />
                  </el-select>
                </el-col>
                <el-col :span="8">
                  <el-button type="primary" @click="addJob" style="width: 100%">Add</el-button>
                </el-col>
              </el-form-item>
              <el-form-item label="System Agent">
                <el-col :span="16">
                  <el-select v-model="selectedSystemAgent" placeholder="Select System Agent" style="width: 100%">
                    <el-option
                        v-for="system_agent in jobList"
                        :key="system_agent.id"
                        :label="'System Agent' + system_agent.id"
                        :value="system_agent.id"
                    />
                  </el-select>
                </el-col>
                <el-col :span="8">
                  <el-button type="primary" @click="addJob" style="width: 100%">Add</el-button>
                </el-col>
              </el-form-item>

            </el-form>


          </el-card>
          <!-- Job Control -->
          <el-card class="panel-card mt-3" shadow="hover">
            <div class="panel-header">
              <span>Job Control</span>
            </div>
            <el-row :gutter="8" align="middle">
              <el-col :span="16">
                <el-select v-model="selectedJob" placeholder="Select Job" style="width: 100%">
                  <el-option
                      v-for="job in jobList"
                      :key="job.id"
                      :label="'Job ' + job.id"
                      :value="job.id"
                  />
                </el-select>
              </el-col>
              <el-col :span="8">
                <el-button type="primary" @click="addJob" style="width: 100%">Add</el-button>
              </el-col>
            </el-row>
          </el-card>

          <!-- Job Pools -->
          <el-card class="panel-card mt-3" shadow="hover">
            <div class="panel-header">
              <span>Job Pools</span>
            </div>
            <el-collapse>
              <el-collapse-item
                  v-for="(jobs, jobId) in jobDict"
                  :key="jobId"
                  :name="jobId"
              >
                <template #title>
                  <span>Job Pool {{ jobId }}</span>
                </template>
                <div v-for="job in jobs" :key="job.id" class="job-item">
                  <div class="job-info">
                    <span>Job {{ job.id }}</span>
                    <span :class="job.status === 'FINISHED' ? 'status-finished' : 'status-processing'">
                    {{ job.status === 'FINISHED' ? 'Finished' : 'Processing...' }}
                  </span>
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

        <!-- 右侧工厂地图 -->
        <el-col :span="18">
          <el-card class="map-card" shadow="hover">
            <div class="map-header">
              <span>Current Factory Map</span>
              <div class="map-controls">
              </div>
            </div>
            <div class="map-container">
              <div v-html="svgPic" class="map-container"></div>

              <!--              <el-image :src="map_src" style="width: 100%; height: 100%;" fit="cover"/>-->
            </div>
          </el-card>
        </el-col>
      </el-row>
    </div>
  </div>
</template>

<script setup>
import {
  ElButton, ElCol, ElInput, ElMessage, ElRow, ElTable, ElTableColumn, ElTag, ElTooltip, ElImage,
} from "element-plus";

import {ref, onMounted, onUnmounted} from "vue";
import {UploadFilled} from '@element-plus/icons-vue'
import {useFactoryState} from "/@/stores/factoryState.ts"

const stores = useFactoryState()
const svgPic = ref('')
let timer = null

const factoryStart = async () => {
  const res = await fetch('/api/factory/start', {method: 'POST'})
  const data = await res.json()
  ElMessage.success(data.message)
  // 启动自动轮询刷新
  startPolling()
}

const factoryPause = async () => {
  const res = await fetch('/api/factory/pause', {method: 'POST'})
  const data = await res.json()
  ElMessage.info(data.message)
}

const factoryResume = async () => {
  const res = await fetch('/api/factory/resume', {method: 'POST'})
  const data = await res.json()
  ElMessage.success(data.message)
}

const factoryReset = async () => {
  const res = await fetch('/api/factory/reset', {method: 'POST'})
  const data = await res.json()
  ElMessage.warning(data.message)
}
// 渲染工厂地图
const factoryRender = async () => {
  try {
    const res = await fetch('/api/map/render', {method: 'POST'})
    const data = await res.json()
    console.log(data)
    if (data.svg_pic) {
      svgPic.value = data.svg_pic
      ElMessage.success(data.message)
    }
  } catch (error) {
    console.error(error)
    ElMessage.error("渲染失败 ❌")
  }
}

// 开启轮询（每隔3秒刷新一次）
function startPolling() {
  clearPolling()
  timer = setInterval(async () => {
    try {
      const res = await fetch('/api/map/render', {method: 'POST'})
      const data = await res.json()
      svgPic.value = data.svg_pic
    } catch (e) {
      console.warn('刷新图像失败', e)
    }
  }, 1000)
}

function clearPolling() {
  if (timer) {
    clearInterval(timer)
    timer = null
  }
}

onUnmounted(() => {
  clearPolling()
})
</script>

<style scoped>
h3 {
  font-size: 24px;
  color: #333;
  margin-bottom: 20px;
}

.factory-container {
  padding: 20px;
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

.panel-card {
  border-radius: 12px;
}

.upload-config-box {
  padding: 20px;
  background-color: #f0f8ff; /* 浅蓝背景 */
  border-radius: 12px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
  margin: 0 auto;
}

.new-dag-font-style {
  font-size: 16px;
  margin-bottom: 15px;
  font-weight: bold;
}

.panel-card .panel-header {
  font-weight: bold;
  font-size: 16px;
  margin-bottom: 12px;
}

.mt-3 {
  margin-top: 16px;
}

.job-item {
  margin-bottom: 12px;
}

.job-info {
  display: flex;
  justify-content: space-between;
  margin-bottom: 4px;
}

.status-finished {
  color: green;
  font-weight: bold;
}

.status-processing {
  color: #409EFF;
  font-weight: bold;
}

.map-card {
  height: 100%;
  display: flex;
  flex-direction: column;
}

.map-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
  font-weight: bold;
  font-size: 18px;
}

.map-controls {
  display: flex;
  gap: 12px;
  align-items: center;
}

.map-container {
  width: 100%;
  height: 600px;
  background: #fafafa;
  border-radius: 12px;
  overflow: hidden;
}
</style>