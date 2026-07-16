<template>
  <div class="data-panel">
    <div class="panel-header">
      <h3>⚙️ 数据与配置</h3>
    </div>

    <div class="panel-content">
      <!-- ===== 数据源 ===== -->
      <div class="section-block">
        <div class="section-title"><i class="el-icon-folder-opened"></i> 数据源</div>

        <!-- FJSP 任务选择 -->
        <div class="data-source-row">
          <label>任务实例</label>
          <div class="data-source-selects">
            <el-select
              v-model="selectedFjspCategory"
              placeholder="选择类别"
              size="small"
              @change="onFjspCategoryChange"
            >
              <el-option
                v-for="cat in fjspCategories"
                :key="cat"
                :label="cat"
                :value="cat"
              />
            </el-select>
            <el-select
              v-model="selectedFjspInstance"
              placeholder="选择实例"
              size="small"
              filterable
            >
              <el-option
                v-for="inst in currentFjspInstances"
                :key="inst"
                :label="inst"
                :value="inst"
              />
            </el-select>
          </div>
        </div>

        <!-- MAPF 地图选择 -->
        <div class="data-source-row">
          <label>地图</label>
          <div class="data-source-selects">
            <el-select
              v-model="selectedMapCategory"
              placeholder="选择类别"
              size="small"
              @change="onMapCategoryChange"
            >
              <el-option
                v-for="cat in mapCategories"
                :key="cat"
                :label="cat"
                :value="cat"
              />
            </el-select>
            <el-select
              v-model="selectedMapName"
              placeholder="选择地图"
              size="small"
              filterable
            >
              <el-option
                v-for="m in currentMapNames"
                :key="m"
                :label="m"
                :value="m"
              />
            </el-select>
          </div>
        </div>

        <!-- 参数 -->
        <div class="data-source-row data-source-params">
          <div class="param-item">
            <label>AGV 数量</label>
            <el-input-number v-model="numAgvs" :min="1" :max="20" size="small" controls-position="right" />
          </div>
          <div class="param-item">
            <label>随机种子</label>
            <el-input-number v-model="seed" :min="0" size="small" controls-position="right" />
          </div>
        </div>

        <slot name="data-source-extra"></slot>

        <!-- 生成 / 导出按钮 -->
        <div class="action-buttons">
          <el-button size="small" :disabled="!canGenerate && !isGenerating" @click="resetDataSource"> ✕ 重置</el-button>
          <el-button
            size="small"
            :disabled="!store.currentConfig"
            @click="exportConfig"
          >
            📤 导出配置
          </el-button>
          <el-button
            size="small"
            type="primary"
            :loading="isGenerating"
            :disabled="!canGenerate"
            @click="generateConfig"
          >
            {{ isGenerating ? '生成中...' : '✓ 生成配置' }}
          </el-button>
        </div>
      </div>

      <!-- ===== 生产线配置管理 ===== -->
      <div class="section-block">
        <div class="section-title"><i class="el-icon-upload"></i> 生产线配置管理</div>

        <!-- 文件上传区域 -->
        <div
          class="upload-area"
          @dragover.prevent="dragover = true"
          @dragleave.prevent="dragover = false"
          @drop.prevent="handleDrop"
          :class="{ 'drag-active': dragover }"
        >
          <input
            type="file"
            ref="fileInput"
            accept=".json"
            @change="handleFileSelect"
            style="display: none"
          />

          <div class="upload-icon">📋</div>
          <p class="upload-text">
            <span class="browse-link" @click="$refs.fileInput.click()"> 点击上传 </span>
            或拖拽配置文件到此处
          </p>
          <p class="upload-hint">支持格式: .json (工厂配置文件)</p>
        </div>

        <!-- 文件预览 -->
        <div v-if="selectedFile" class="file-preview">
          <div class="preview-item">
            <span class="preview-label">文件名:</span>
            <span class="preview-value">{{ selectedFile.name }}</span>
          </div>
          <div class="preview-item">
            <span class="preview-label">文件大小:</span>
            <span class="preview-value">{{ (selectedFile.size / 1024).toFixed(2) }} KB</span>
          </div>
        </div>

        <!-- 操作按钮 -->
        <div class="action-buttons">
          <el-button size="small" :disabled="!selectedFile" @click="resetFile"> ✕ 清除 </el-button>
          <el-button size="small" type="success" plain @click="downloadTemplate">
            📥 下载模板
          </el-button>
          <el-button
            size="small"
            type="primary"
            :loading="isLoading"
            :disabled="!selectedFile || isLoading"
            @click="uploadConfig"
          >
            {{ isLoading ? '处理中...' : '✓ 上传配置' }}
          </el-button>
        </div>

        <!-- 错误提示 -->
        <div v-if="validationError" class="error-alert">
          <div class="error-icon">⚠️</div>
          <div class="error-content">
            <p class="error-title">配置验证失败</p>
            <p class="error-detail">{{ validationError }}</p>
          </div>
          <button class="error-close" @click="validationError = null">✕</button>
        </div>

        <!-- 成功提示 -->
        <div v-if="successMessage" class="success-alert">
          <div class="success-icon">✓</div>
          <div class="success-content">
            <p class="success-title">配置加载成功</p>
            <p class="success-detail">{{ successMessage }}</p>
          </div>
          <button class="success-close" @click="successMessage = null">✕</button>
        </div>
      </div>

      <!-- ===== 已加载配置列表 ===== -->
      <div class="section-block" v-if="loadedConfigs.length > 0">
        <div class="section-title"><i class="el-icon-s-grid"></i> 已加载的配置</div>
        <div class="config-list">
          <div v-for="config in loadedConfigs" :key="config.id" class="config-item">
            <div class="config-info">
              <div class="config-name">{{ config.name }}</div>
              <div class="config-meta">
                <span class="config-version">v{{ config.version || '1.0' }}</span>
                <span class="config-id">ID: {{ config.id }}</span>
              </div>
            </div>
            <el-button
              size="small"
              :type="currentConfigId === config.id ? 'primary' : 'default'"
              :loading="isLoading"
              :disabled="isLoading"
              @click="selectConfig(config.id)"
            >
              {{ currentConfigId === config.id ? '✓ 使用中' : '使用' }}
            </el-button>
          </div>
        </div>
      </div>

      <!-- ===== 工厂资产（独立组件） ===== -->
      <FactoryAssetPanel @edit-mode-change="onEditModeChange" />
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { useFactoryStore } from '@/stores/factory'
import { validateAndNormalizeConfig } from '@/utils/configValidator'
import { apiPost, API_ROUTES } from '@/utils/api'
import FactoryAssetPanel from './FactoryAssetPanel.vue'

// --- Store ---
const store = useFactoryStore()

// --- Emits (向上传递编辑模式状态) ---
const emit = defineEmits(['edit-mode-change', 'config-loaded'])
function onEditModeChange(val) {
  emit('edit-mode-change', val)
}

// --- Props & Emits ---
const props = defineProps({
  services: {
    type: Array,
    default: () => [
      { name: 'AGV_01', description: '自动导引车 1号' },
      { name: 'Arm_Robot_A', description: '机械臂 A' },
      { name: 'Storage_Unit', description: '仓储单元' },
      { name: 'Quality_Cam', description: '质检相机' },
    ],
  },
})

// --- Upload State ---
const fileInput = ref(null)
const selectedFile = ref(null)
const dragover = ref(false)
const isLoading = ref(false)
const validationError = ref(null)
const successMessage = ref(null)

// --- 数据源 State ---
const isGenerating = ref(false)

const selectedFjspCategory = ref(null)
const selectedFjspInstance = ref(null)
const selectedMapCategory = ref(null)
const selectedMapName = ref(null)
const numAgvs = ref(4)
const seed = ref(42)

const fjspCategories = computed(() => Object.keys(store.datasetList?.fjsp_instances || {}))
const currentFjspInstances = computed(() =>
  (store.datasetList?.fjsp_instances || {})[selectedFjspCategory.value] || [],
)
const mapCategories = computed(() => Object.keys(store.datasetList?.mapf_maps || {}))
const currentMapNames = computed(() =>
  (store.datasetList?.mapf_maps || {})[selectedMapCategory.value] || [],
)
const canGenerate = computed(() => selectedFjspInstance.value && selectedMapName.value)

// --- Computed ---
const loadedConfigs = computed(() => {
  return Object.values(store.factoryConfigs || {})
})

const currentConfigId = computed(() => store.currentConfigId)

// --- Methods ---
function handleFileSelect(event) {
  const files = event.target.files
  if (files && files.length > 0) {
    selectedFile.value = files[0]
    validationError.value = null
  }
}

function handleDrop(event) {
  dragover.value = false
  const files = event.dataTransfer.files
  if (files && files.length > 0) {
    const file = files[0]
    if (file.type === 'application/json' || file.name.endsWith('.json')) {
      selectedFile.value = file
      validationError.value = null
    } else {
      validationError.value = '请上传 JSON 文件'
    }
  }
}

function resetFile() {
  selectedFile.value = null
  validationError.value = null
  if (fileInput.value) {
    fileInput.value.value = ''
  }
}

function uploadConfig() {
  if (!selectedFile.value) return

  isLoading.value = true
  validationError.value = null
  successMessage.value = null

  const reader = new FileReader()

  reader.onload = async (e) => {
    try {
      const jsonData = JSON.parse(e.target.result)
      const config = validateAndNormalizeConfig(jsonData)

      // 1. 加载到 Store（前端渲染）
      store.loadConfigFromFile(config)
      emit('config-loaded', config)

      // 2. 上传到后端
      const response = await apiPost(API_ROUTES.FACTORY_CONFIG_UPLOAD, {
        filename: selectedFile.value.name,
        config: config,
      })

      if (response.status === 'ok') {
        successMessage.value = `✅ 配置上传成功: ${config.name}`
        resetFile()

        // 自动隐藏成功信息
        setTimeout(() => {
          successMessage.value = null
        }, 3000)
      } else {
        throw new Error(response.message || '上传失败')
      }
    } catch (error) {
      validationError.value = error.message || '配置上传失败'
      console.error('Configuration error:', error)
    } finally {
      isLoading.value = false
    }
  }

  reader.onerror = () => {
    validationError.value = '文件读取失败，请重试'
    isLoading.value = false
  }

  reader.readAsText(selectedFile.value)
}

async function selectConfig(configId) {
  const config = store.factoryConfigs[configId]
  if (!config) {
    ElMessage.error('配置不存在')
    return
  }

  isLoading.value = true

  try {
    // 1. 更新本地 store
    store.setCurrentConfig(configId)
    emit('config-loaded', config)

    // 2. 同步到后端
    const response = await apiPost(API_ROUTES.FACTORY_CONFIG_UPLOAD, {
      filename: `${config.name || configId}.json`,
      config: config,
    })

    if (response.status === 'ok') {
      ElMessage.success(`已切换到配置: ${config.name || configId}`)
    } else {
      throw new Error(response.message || '切换配置失败')
    }
  } catch (error) {
    console.error('切换配置失败:', error)
    ElMessage.error(`切换配置失败: ${error.message}`)
  } finally {
    isLoading.value = false
  }
}

function downloadTemplate() {
  // 创建示例模板
  const template = {
    id: 'my_factory',
    name: '我的工厂',
    version: '1.0.0',
    description: '工厂描述',
    topology: {
      gridWidth: 20,
      gridHeight: 14,
      zones: [
        {
          id: 'zone_1',
          name: '示例禁区',
          area: { x: 1, y: 1, w: 3, h: 3 },
          type: 'restricted',
          color: 'rgba(255, 235, 59, 0.15)',
        },
      ],
      machines: {
        MACHINE_1: {
          id: 'MACHINE_1',
          name: '机器 01',
          location: [5, 5],
          size: [2, 2],
          status: 'IDLE',
        },
        MACHINE_2: {
          id: 'MACHINE_2',
          name: '机器 02',
          location: [10, 5],
          size: [2, 2],
          status: 'IDLE',
        },
      },
      waypoints: {
        WP_1: { location: [1, 1], type: 'dock', name: '上货点' },
      },
    },
    agvs: [
      {
        id: 0,
        name: 'AGV-01',
        initialLocation: [5, 2],
        velocity: 1.0,
        capacity: 100,
        status: 'IDLE',
      },
      {
        id: 1,
        name: 'AGV-02',
        initialLocation: [15, 12],
        velocity: 1.0,
        capacity: 100,
        status: 'IDLE',
      },
    ],
    // 任务配置示例
    jobs: {
      job_list: [
        {
          job_id: 0,
          name: '示例任务-01',
          operations: [
            { name: '工序1-加工', machine_options_with_time: [[0, 5], [1, 7]] },
            { name: '工序2-组装', machine_options_with_time: [[1, 3], [0, 6]] },
          ],
          arrival_time: 0,
          due_time: 50,
          priority: 1,
        },
      ],
    },
    // 异常配置示例。使用 exception_config，避免和前端日志/状态事件 event 混淆。
    exception_config: {
      preset: 'no_event',
    },
    // 加工时间波动配置。不是 Exception；用于工序开始加工时采样实际加工时长。
    processing_time_config: {
      preset: 'none',
    },
    simulation_control: {
      max_steps: 1000,
    },
    renderConfig: {
      baseGridSize: 40,
      colors: {},
    },
  }

  // 下载为 JSON 文件
  const dataStr = JSON.stringify(template, null, 2)
  const dataBlob = new Blob([dataStr], { type: 'application/json' })
  const url = URL.createObjectURL(dataBlob)
  const link = document.createElement('a')
  link.href = url
  link.download = 'factory_config_template.json'
  link.click()
  URL.revokeObjectURL(url)

  ElMessage.success('模板下载成功')
}

// --- 数据源 Methods ---
function resetDataSource() {
  selectedFjspCategory.value = null
  selectedFjspInstance.value = null
  selectedMapCategory.value = null
  selectedMapName.value = null
  numAgvs.value = 4
  seed.value = 42
}

function onFjspCategoryChange(cat) {
  selectedFjspInstance.value = null
  const instances = (store.datasetList?.fjsp_instances || {})[cat]
  if (instances && instances.length > 0) {
    selectedFjspInstance.value = instances[0]
  }
}

function onMapCategoryChange(cat) {
  selectedMapName.value = null
  const names = (store.datasetList?.mapf_maps || {})[cat]
  if (names && names.length > 0) {
    selectedMapName.value = names[0]
  }
}

async function loadDatasets() {
  try {
    await store.fetchDatasets()
  } catch (e) {
    console.error('加载数据集失败:', e)
  }
}

async function generateConfig() {
  if (!canGenerate.value) return
  isGenerating.value = true
  validationError.value = null
  successMessage.value = null
  try {
    const { config } = await apiPost(API_ROUTES.DATASET_GENERATE, {
      fjsp_category: selectedFjspCategory.value,
      fjsp_instance: selectedFjspInstance.value,
      map_category: selectedMapCategory.value,
      map_name: selectedMapName.value,
      num_agvs: numAgvs.value,
      seed: seed.value,
    })
    // 1. 清空旧配置，保存到前端 Store
    store.factoryConfigs = {}
    store.reset()
    store.loadConfigFromFile(config)
    emit('config-loaded', config)
    store.initializeAGVs()
    // 2. 上传到后端
    const response = await apiPost(API_ROUTES.FACTORY_CONFIG_UPLOAD, {
      filename: `${config.id || 'generated'}.json`,
      config: config,
    })
    if (response.status !== 'ok') {
      throw new Error(response.message || '后端同步失败')
    }
    successMessage.value = `配置生成成功: ${config.name || config.id}`
    setTimeout(() => {
      successMessage.value = null
    }, 3000)
  } catch (e) {
    validationError.value = `生成失败: ${e.message}`
  } finally {
    isGenerating.value = false
  }
}

onMounted(() => {
  loadDatasets()
})

function exportConfig() {
  const config = store.exportCurrentConfig()
  if (!config) {
    ElMessage.warning('没有可导出的配置')
    return
  }
  const dataStr = JSON.stringify(config, null, 2)
  const blob = new Blob([dataStr], { type: 'application/json' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = `${config.id || 'factory_config'}.json`
  link.click()
  URL.revokeObjectURL(url)
  ElMessage.success('配置已导出')
}

/**
 * 暴露给父组件的方法
 */
function getSelectedFile() {
  return selectedFile.value
}

// 暴露方法给父组件
defineExpose({
  getSelectedFile,
  resetFile,
})
</script>

<style scoped>
@import './styles/ConfigPanel.css';
/* ===== 新增样式 ===== */
</style>
