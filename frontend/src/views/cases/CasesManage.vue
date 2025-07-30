<template>
  <div class="outline">
    <div>
      <h3>Typical Cases</h3>
    </div>

    <div>
      <div class="new-dag-font-style">Standard Config Sets</div>
      <div class="upload-config-box">

        <el-card
            v-for="(config, index) in configs"
            :key="index"
        >
          <template #header>
            <div class="card-header">
              <el-tag>Config Set {{ index + 1 }}</el-tag>
            </div>
          </template>
          <el-row type="flex" justify="center" align="middle" style="height: 100%;">
            <el-col :span="12" style="display: flex; justify-content: center; align-items: center;">
              <div class="block" style="width: 100%; height: 80%;">
                <!-- 使用 mapSrcs[index] 绑定图片源 -->
                <el-image
                    :src="mapSrcs[index]"
                    style="width: 100%; height: 100%;"
                    fit="cover"
                ></el-image>
              </div>
            </el-col>
            <el-col :span="1"></el-col>
            <el-col :span="11" style="display: flex; justify-content: center; align-items: center;">
              <!-- 按钮点击时传入对应的参数 -->
              <el-row>
                <el-col>
                  <el-card>
                    <template #header>
                      <div>
                        <el-row>
                          <el-col :span="9">
                            <el-tag>{{config.factoryName}}</el-tag>
                          </el-col>
                          <el-col :span="2">

                          </el-col>
                          <el-col :span="13">
                            <el-button
                                type="success"
                                icon="el-icon-download"
                                plain
                                @click="getStandardConfig(config.buttonParam)"
                                style="width: 100%;"
                            >
                              {{config.buttonText}}
                            </el-button>
                          </el-col>
                        </el-row>

                      </div>
                    </template>
                    <el-descriptions
                        title="Scenario Info"
                        direction="vertical"
                        :column="4"
                        border
                    >
                      <el-descriptions-item label="MachineNumber">{{config.machineNumber}}</el-descriptions-item>
                      <el-descriptions-item label="AGVNumber">{{config.agvNumber}}</el-descriptions-item>
                      <el-descriptions-item label="FactorySize" :span="2">{{config.factorySize}}</el-descriptions-item>
                      <el-descriptions-item label="FactoryInfo">
                        <el-tag size="small">{{config.factoryInfo}}</el-tag>
                      </el-descriptions-item>
                      <el-descriptions-item label="Description">
                        {{config.description}}
                      </el-descriptions-item>
                    </el-descriptions>
                  </el-card>


                </el-col>

              </el-row>

            </el-col>
          </el-row>
          <br/>
        </el-card>

      </div>
    </div>
  </div>
</template>

<script>
import {
  ElButton, ElCol, ElInput, ElMessage, ElRow, ElTable, ElTableColumn, ElTag, ElTooltip, ElImage,
} from "element-plus";

import {nextTick, ref, onMounted, onUnmounted} from "vue";
import {ControlButton, Controls} from "@vue-flow/controls";
import {Background} from "@vue-flow/background";
import {MiniMap} from "@vue-flow/minimap";
import {Connection, Link, MagicStick, Right, Picture as IconPicture} from '@element-plus/icons-vue';
import {UploadFilled} from '@element-plus/icons-vue'

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
    Background,
    MiniMap,
    ControlButton,
    Controls,
    Connection,
    Link,
    Right,
    MagicStick,
    UploadFilled,
    IconPicture
  },
  setup() {
    const configs = ref([
      {
        mapParam: 'map1', // 用于生成图片URL的参数
        buttonText: 'Get Standard Config 1',
        buttonParam: {type: 'custom_config_1'}, // 传给下载函数的参数

        factoryName: 'Standard Config 1',

        machineNumber: 5,
        agvNumber: 2,
        factorySize: '30*20',
        factoryInfo: 'Pipeline',
        description: 'Single Pipeline Job.'
      },
      {
        mapParam: 'map2',
        buttonText: 'Get Standard Config 2',
        buttonParam: {type: 'custom_config_2'},

        factoryName: 'Standard Config 2',

        machineNumber: 6,
        agvNumber: 4,
        factorySize: '30*20',
        factoryInfo: 'Cycle',
        description: 'Single Cycle Job.'
      },
      // 可以添加更多配置
    ]);

    const mapSrcs = ref([]);

    configs.value.forEach((config, index) => {
      // 根据 mapParam 生成初始图片URL
      const initialSrc = `/api/cases/image?map=${config.mapParam}`;
      mapSrcs.value[index] = initialSrc;
    });

    onMounted(() => {
    });
    onUnmounted(() => {
    });

    const getStandardConfig = (params) => {
      const queryString = new URLSearchParams(params).toString();

      fetch(`/api/cases/config?${queryString}&_t=${Date.now()}`, {
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


    return {
      configs,
      mapSrcs,
      getStandardConfig,
    };
  },

  data() {
    return {};
  },

  methods: {}
  ,
  mounted() {
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
