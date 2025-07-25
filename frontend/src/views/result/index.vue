<template>
  <div class="home-container layout-pd">
    <!-- Data Source Selection Row -->
    <el-row :gutter="15" class="home-card-two mb15">
      <el-col :xs="24" :sm="24" :md="20" :lg="20" :xl="20">
        <div class="home-card-item data-source-container"
             :class="{ 'source-loading': isSourceLoading }">
          <div class="flex-margin flex w100">
            <div class="flex-auto" style="font-weight: bold">
              Choose Datasource: &nbsp;
              <el-select
                  v-model="selectedDataSource"
                  :disabled="isSourceLoading"
                  placeholder="Please choose datasource"
                  class="compact-select"
              >
                <el-option
                    v-for="item in dataSourceList"
                    :key="item.id"
                    :label="item.label"
                    :value="item.id"
                />
              </el-select>

              <el-button
                  ref="uploadButton"
                  type="primary"
                  :disabled="!selectedDataSource"
                  @click="triggerConfigUpload"
                  style="margin-left: 15px"
              >
                Upload Config
                <template #loading>
                  <i class="el-icon-loading"></i>
                </template>
              </el-button>


              <input
                  ref="uploadInput"
                  type="file"
                  hidden
                  @change="handleFileUpload"
              >
            </div>
            <div v-if="isSourceLoading" class="loading-overlay">
              <i class="el-icon-loading"></i>
              <span>Loading Visualizations...</span>
            </div>
          </div>
        </div>
      </el-col>
      <el-col :xs="24" :sm="24" :md="4" :lg="4" :xl="4">
        <div class="home-card-item export-container">
          <el-button
              type="primary"
              class="export-button"
              @click="exportTaskLog"
          >
            Export Log
          </el-button>
        </div>
      </el-col>
    </el-row>

    <!-- Visualization Controls Row -->
    <el-row class="viz-controls-row mb15">
      <el-col :span="24">
        <div class="viz-controls-panel">
          <div class="control-group">
            <h4>Active Visualizations:</h4>
            <el-checkbox-group v-model="currentActiveVisualizationsArray">
              <el-checkbox
                  v-for="viz in currentVisualizationConfig"
                  :key="viz.id"
                  :label="viz.id"
                  class="module-checkbox"
              >
                {{ viz.name }}
              </el-checkbox>
            </el-checkbox-group>
          </div>
        </div>
      </el-col>
    </el-row>

    <!-- Visualization Modules Row -->
    <el-row :gutter="15" class="home-card-two mb15">

      <template v-if="!isSourceLoading">
        <el-col
            v-for="viz in currentVisualizationConfig"
            :key="getVizKey(viz)"
            :xs="24"
            :sm="24"
            :md="getVisualizationSpan(viz.size, 'md')"
            :lg="getVisualizationSpan(viz.size, 'lg')"
            :xl="getVisualizationSpan(viz.size, 'xl')"
            v-show="componentsLoaded && currentActiveVisualizations.has(viz.id)"
        >
          <div class="home-card-item viz-module">
            <div class="viz-module-header">
              <h3 class="viz-title">{{ viz.name }}</h3>
              <component
                  :is="vizControls[viz.type]"
                  :key="viz.type + '-' + viz.variablesHash"
                  v-if="vizControls[viz.type] && selectedDataSource"
                  :config="viz"
                  :variable-states="variableStates[selectedDataSource]?.[viz.id] || {}"
                  @update:variable-states="updateVariableStates(viz.id, $event)"
              />
            </div>

            <component
                :is="visualizationComponents[viz.type]"
                v-if="componentsLoaded && visualizationComponents[viz.type] && selectedDataSource"
                :key="`${viz.type}-${selectedDataSource}-${viz.id}-${viz.variablesHash}`"
                :config="viz"
                :data="processedData[viz.id]"
                :variable-states="variableStates[selectedDataSource]?.[viz.id] || {}"
            />
          </div>
        </el-col>
      </template>

      <template v-else>
        <el-col :span="24">
          <div class="skeleton-loading">
            <div class="skeleton-item" v-for="n in 3" :key="n"></div>
          </div>
        </el-col>
      </template>
    </el-row>
    
    <el-card style="max-width: 480px; margin-top: 10px">
      <div style="font-size: 16px; font-weight: bold; margin-bottom: 10px">Job Process</div>
      <div v-for="job in jobProgressList" :key="job.id" style="margin-bottom: 15px">
        <div style="display: flex; justify-content: space-between; align-items: center;">
          <span>Job {{ job.id }}</span>
          <span v-if="job.status === 'FINISHED'" style="color: green;">Finished</span>
          <span v-else style="color: blue;">Processing...</span>
        </div>
        <el-progress :percentage="job.progress" :status="job.status === 'FINISHED' ? 'success' : undefined" />
      </div>
    </el-card>
  </div>
</template>

<script>
import {markRaw, reactive, toRaw, watch} from 'vue'
import mitt from 'mitt'
import {ElMessage} from "element-plus";

const emitter = mitt()

export default {
  data() {
    return {
      selectedDataSource: null,
      dataSourceList: [],
      bufferedTaskCache: reactive({}),
      maxBufferedTaskCacheSize: 20,
      componentsLoaded: false,
      visualizationConfig: {},
      activeVisualizations: {},
      variableStates: {},
      visualizationComponents: {},
      vizControls: {},
      pollingInterval: null,

      isSourceLoading: false,
      isUploading: false,

      
      jobProgressList: [], // 存储从接口获取的 Job 进度数据
      progressInterval: null, // 用于保存定时器引用
    }
  },
  computed: {
    processedData() {
      const result = {}
      this.currentVisualizationConfig.forEach(viz => {
        result[viz.id] = this.processVizData(viz)
      })
      return result
    },
    currentVisualizationConfig() {
      return this.visualizationConfig[this.selectedDataSource] || []
    },
    currentActiveVisualizations() {
      console.log('activeVisualizations:', this.activeVisualizations[this.selectedDataSource])
      return this.activeVisualizations[this.selectedDataSource] || new Set()
    },
    currentActiveVisualizationsArray: {
      get() {
        return Array.from(this.currentActiveVisualizations)
      },
      set(newVal) {
        this.activeVisualizations[this.selectedDataSource] = new Set(newVal)
      }
    },
  },

  async created() {
    this.dataSourceList.forEach(source => {
      this.bufferedTaskCache[source.id] = reactive([])
    })

    watch(
        () => this.bufferedTaskCache,
        (newVal) => {
          // console.log('Cache updated:', newVal)
        },
        {deep: true}
    )

    await this.autoRegisterComponents()
    this.componentsLoaded = true
    // await this.fetchDataSourceList()
    // this.setupDataPolling()

    emitter.on('force-update-charts', () => {
      this.$nextTick(() => {
        if (!this.selectedDataSource) return
        this.currentVisualizationConfig.forEach(viz => {
          this.variableStates[this.selectedDataSource][viz.id] =
              {...this.variableStates[this.selectedDataSource][viz.id]}

        })
      })

    })

  },
  watch: {
    selectedDataSource(newVal) {
      if (newVal) {
        this.handleSourceChange(newVal)
      }
    }
  },
  methods: {
    calculateVariablesHash(variables) {
      return [...variables].sort().join('|');
    },

    getVizKey(viz) {
      return `${viz.id}-${viz.variablesHash}-${viz.size}`;
    },

    arraysEqual(a, b) {
      if (a === b) return true;
      if (!Array.isArray(a) || !Array.isArray(b)) return false;
      if (a.length !== b.length) return false;
      const sortedA = [...a].sort();
      const sortedB = [...b].sort();
      return sortedA.every((val, i) => val === sortedB[i]);
    },
    triggerConfigUpload() {
      if (!this.selectedDataSource) return
      this.$refs.uploadInput.value = null
      this.$refs.uploadInput.click()
    },

    async handleFileUpload(event) {
      const file = event.target.files[0]
      if (!file) return

      try {
        const formData = new FormData()
        formData.append('file', file)

        this.$refs.uploadButton.loading = true

        fetch(`/api/result_visualization_config/${this.selectedDataSource}`, {
          method: 'POST',
          body: formData
        })
            .then(response => response.json())
            .then(data => {
              const state = data['state']
              const msg = data['msg']
              this.fetchVisualizationConfig(this.selectedDataSource)
              this.showMsg(state, msg);
            })
      } catch (error) {
        ElMessage.error("System Error")
        console.log(error);
      } finally {
        this.$refs.uploadButton.loading = false
      }
    },
    async handleSourceChange(sourceId) {
      if (!sourceId || !this.dataSourceList.some(s => s.id === sourceId)) {
        console.error('Invalid source selection')
        return
      }

      this.isSourceLoading = true

      try {
        await this.fetchVisualizationConfig(sourceId)
      } catch (e) {
        console.error('Source change failed:', e)
      } finally {
        this.isSourceLoading = false // 结束加载
      }

      // 强制更新视图
      this.$nextTick(() => {
        emitter.emit('force-update-charts')
      })
    },
    getVisualizationSpan(size, breakpoint) {
      const baseSize = size || 1
      // 大屏显示完整尺寸，中小屏自动调整
      switch (breakpoint) {
        case 'xl':
          return Math.min(24, baseSize * 8)
        case 'lg':
          return Math.min(24, (baseSize > 2 ? 24 : baseSize * 8))
        default: // md及以下
          return baseSize > 1 ? 24 : 8
      }
    },
    async autoRegisterComponents() {
      try {
        const modules = import.meta.glob('./visualization/*Template.vue')
        const controls = import.meta.glob('./visualization/*Controls.vue')

        await Promise.all([
          ...Object.entries(modules).map(async ([path, loader]) => {
            const type = path.split('/').pop().replace('Template.vue', '').toLowerCase()
            try {
              const comp = await loader()
              this.visualizationComponents[type] = markRaw(comp.default)
              console.log('Successfully registered:', type)
            } catch (e) {
              console.error(`Failed to load ${type} template:`, e)
            }
          }),
          ...Object.entries(controls).map(async ([path, loader]) => {
            const type = path.split('/').pop().replace('Controls.vue', '').toLowerCase()
            try {
              const comp = await loader()
              this.vizControls[type] = markRaw(comp.default)
              console.log('Successfully registered control:', type)
            } catch (e) {
              console.error(`Failed to load ${type} control:`, e)
            }
          })
        ])
      } catch (error) {
        console.error('Component auto-registration failed:', error)
      }
    },


    processVizData(vizConfig) {
      const sourceId = this.selectedDataSource
      if (!sourceId || !this.bufferedTaskCache[sourceId]) return []

      const validVizIds = new Set(this.currentVisualizationConfig.map(v => String(v.id)))
      const filteredData = this.bufferedTaskCache[sourceId]
          .filter(task => {
            return task.data?.some(item =>
                validVizIds.has(String(item.id)) &&
                String(item.id) === String(vizConfig.id))
          })
          .map(task => {
            const vizDataItem = task.data.find(item => String(item.id) === String(vizConfig.id))
            return {
              taskId: String(task.task_id),
              ...(vizDataItem?.data || {})
            }
          })

      return filteredData
    },

    updateVariableStates(vizId, newStates) {
      if (!this.selectedDataSource) return

      const validVars = this.currentVisualizationConfig
          .find(v => v.id === vizId)
          ?.variables || []

      this.variableStates[this.selectedDataSource][vizId] = validVars.reduce((acc, varName) => {
        acc[varName] = newStates[varName] ?? true
        return acc
      }, {})

      emitter.emit('force-update-charts')
    },

    // async fetchDataSourceList() {
    //   try {
    //     const response = await fetch('/api/source_list')
    //     const data = await response.json()

    //     this.dataSourceList = data.map(source => ({
    //       ...source,
    //       id: String(source.id)
    //     }))
    //     this.dataSourceList.forEach(source => {
    //       this.bufferedTaskCache[source.id] = reactive([])
    //     })
    //   } catch (error) {
    //     console.error('Failed to fetch data sources:', error)
    //   }
    // },

    async fetchVisualizationConfig(sourceId) {
      try {
        const response = await fetch(`/api/result_visualization_config/${sourceId}`)
        const data = await response.json()

        const processedConfig = data.map(viz => reactive({
          ...viz,
          id: String(viz.id),
          variables: [...(viz.variables || [])], // 确保数组可修改
          size: Math.min(3, Math.max(1, parseInt(viz.size) || 1)),
          variablesHash: this.calculateVariablesHash(viz.variables || []) // 新增哈希
        }));


        this.visualizationConfig[sourceId] = processedConfig

        this.activeVisualizations[sourceId] = new Set()
        this.variableStates[sourceId] = reactive({})

        processedConfig.forEach(viz => {
          this.activeVisualizations[sourceId].add(viz.id)

          this.variableStates[sourceId][viz.id] = viz.variables.reduce((acc, varName) => {
            acc[varName] = true
            return acc
          }, {})
        })
        console.log('Initialized variable states:', toRaw(this.variableStates))
      } catch (error) {
        console.error('Failed to fetch visualization config:', error)
      }
    },

    // async getLatestResultData() {
    //   try {
    //     const response = await fetch('/api/task_result')
    //     const data = await response.json()

    //     // 创建新缓存对象保持响应式
    //     const newCache = {...this.bufferedTaskCache}
    //     const configUpdates = {}

    //     Object.entries(data).forEach(([sourceIdStr, tasks]) => {
    //       const sourceId = String(sourceIdStr)
    //       if (!Array.isArray(tasks)) return

    //       const validTasks = tasks
    //           .filter(task => task?.task_id && Array.isArray(task.data))
    //           .map(task => ({
    //             task_id: task.task_id,
    //             data: task.data.map(item => ({
    //               id: String(item.id) || 'unknown',
    //               data: item.data || {}
    //             }))
    //           }))

    //       // 合并新旧数据
    //       newCache[sourceId] = [
    //         ...(newCache[sourceId] || []),
    //         ...validTasks
    //       ].slice(-this.maxBufferedTaskCacheSize)

    //       tasks.forEach(task => {
    //         task.data?.forEach(item => {
    //           const vizId = String(item.id)
    //           const newVariables = Object.keys(item.data || {})

    //           // 查找对应配置
    //           const vizConfig = (this.visualizationConfig[sourceId] || [])
    //               .find(v => v.id === vizId)

    //           if (vizConfig && !this.arraysEqual(vizConfig.variables, newVariables)) {
    //             configUpdates[sourceId] = configUpdates[sourceId] || []
    //             configUpdates[sourceId].push({
    //               vizId,
    //               newVariables
    //             })
    //           }
    //         })
    //       })

    //     })

    //     Object.entries(configUpdates).forEach(([sourceId, updates]) => {
    //       const newConfig = [...(this.visualizationConfig[sourceId] || [])]
    //       updates.forEach(({vizId, newVariables}) => {
    //         const index = newConfig.findIndex(v => v.id === vizId)
    //         if (index !== -1) {
    //           const updatedViz = {
    //             ...newConfig[index],
    //             variables: [...newVariables],
    //             variablesHash: this.calculateVariablesHash(newVariables)
    //           }
    //           newConfig.splice(index, 1, updatedViz)
    //         }
    //       })
    //       this.visualizationConfig[sourceId] = newConfig
    //     })

    //     // 强制替换整个缓存对象
    //     this.bufferedTaskCache = reactive({...newCache})

    //     // 添加可视化配置刷新
    //     if (this.selectedDataSource) {
    //       const sourceId = this.selectedDataSource
    //       if (this.visualizationConfig[sourceId]) {
    //         this.visualizationConfig [sourceId] = this.visualizationConfig[sourceId].map(cfg => ({...cfg}))
    //       }
    //     }

    //     // 添加延迟更新确保DOM刷新
    //     this.$nextTick(() => {
    //       emitter.emit('force-update-charts')
    //     })
    //   } catch (error) {
    //     console.error('Data fetch failed:', error)
    //   }
    // },

    // setupDataPolling() {
    //   this.getLatestResultData()
    //   this.pollingInterval = setInterval(() => {
    //     this.getLatestResultData()
    //   }, 2000)
    // },

    exportTaskLog() {
      fetch('/api/download_log')
          .then(response => response.blob())
          .then(blob => {
            const url = window.URL.createObjectURL(blob)
            const link = document.createElement('a')
            link.href = url
            link.setAttribute('download', 'task_log.json')
            document.body.appendChild(link)
            link.click()
            link.remove()
          })
    },

    showMsg(state, msg) {
      if (state === 'success') {
        ElMessage({
          message: msg,
          showClose: true,
          type: "success",
          duration: 3000,
        });
      } else {
        ElMessage({
          message: msg,
          showClose: true,
          type: "error",
          duration: 3000,
        });
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
      } catch (error) {
        console.error("Failed to retrieve task progress:", error);
      }
    }
  },
  
  mounted() {
    this.fetchJobProgress(); // 首次加载
    this.progressInterval = setInterval(() => {
      this.fetchJobProgress();
    }, 1000); // 每 1 秒刷新一次
  }
  ,
}
</script>

<style scoped>
.home-container {
  overflow: hidden;
  padding: 16px;
}

.data-source-container {
  height: auto;
  padding: 8px 12px;
}

.export-container {
  height: auto;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 8px;
}

.compact-select {
  width: 70%;
}

.compact-select ::v-deep .el-input__inner {
  height: 32px;
  line-height: 32px;
}

.export-button {
  width: 100%;
  padding: 8px 12px;
}

.viz-controls-row {
  margin-top: 20px;
}

.viz-controls-panel {
  background: var(--el-bg-color);
  border-radius: 4px;
  padding: 15px;
  box-shadow: 0 2px 12px 0 rgba(0, 0, 0, .1);
}

.control-group {
  margin-bottom: 8px;
}

.control-group h4 {
  margin-bottom: 10px;
  color: var(--el-text-color-primary);
}

.module-checkbox {
  margin-right: 20px;
  margin-bottom: 8px;
}

.viz-module {
  height: 500px;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  margin-top: 15px;
  transition: all 0.3s ease;
}

.viz-module-header {
  padding: 12px;
  border-bottom: 1px solid var(--el-border-color-light);
}

.viz-title {
  margin: 0 0 8px 0;
  font-size: 1.1em;
  color: var(--el-text-color-primary);
  text-align: center;
}

.home-card-item {
  background: var(--el-bg-color);
  border-radius: 4px;
  border: 1px solid var(--el-border-color-light);
}

/* 确保容器尺寸正确 */
.viz-module {
  height: 500px !important;
  min-height: 500px;
  transform: translateZ(0); /* 触发GPU加速 */
  contain: strict;
}

/* 修复ECharts容器尺寸 */
.chart-wrapper {
  width: 100% !important;
  height: 100% !important;
  min-height: 400px !important;
}

.source-loading {
  position: relative;

  &:after {
    content: "Loading...";
    position: absolute;
    top: 50%;
    left: 50%;
    transform: translate(-50%, -50%);
  }
}

.loading-overlay {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(255, 255, 255, 0.9);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 10;

  i {
    font-size: 24px;
    margin-right: 8px;
    animation: rotating 2s linear infinite;
  }

  span {
    color: var(--el-color-primary);
    font-weight: 500;
  }
}

/* 骨架屏加载动画 */
.skeleton-loading {
  padding: 20px;

  .skeleton-item {
    height: 200px;
    background: #f5f7fa;
    border-radius: 4px;
    margin-bottom: 15px;
    position: relative;
    overflow: hidden;

    &::after {
      content: "";
      position: absolute;
      top: 0;
      left: -100%;
      width: 100%;
      height: 100%;
      background: linear-gradient(
          90deg,
          transparent,
          rgba(255, 255, 255, 0.6),
          transparent
      );
      animation: skeleton-flash 1.5s infinite;
    }
  }
}

/* 动画定义 */
@keyframes rotating {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}

@keyframes skeleton-flash {
  100% {
    left: 100%;
  }
}

/* 原有数据源容器添加定位 */
.data-source-container {
  position: relative; /* 为loading-overlay定位做准备 */
  min-height: 60px; /* 防止加载时高度塌缩 */
}

.upload-config-btn {
  transition: opacity 0.3s ease;

  &.is-disabled {
    opacity: 0.6;
    cursor: not-allowed;
  }
}
</style>