<template>
  <div class="data-panel">
    <div class="panel-header">
      <h3>⚙️ 数据与配置</h3>
    </div>

    <div class="panel-content">
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
              @click="selectConfig(config.id)"
            >
              {{ currentConfigId === config.id ? '✓ 使用中' : '使用' }}
            </el-button>
          </div>
        </div>
      </div>

      <!-- ===== 工厂节点资产 ===== -->
      <div class="section-block flex-grow">
        <div class="section-title">
          <i class="el-icon-s-grid"></i>
          工厂节点资产
          <el-tooltip content="包含逻辑节点与物理设备" placement="top">
            <span class="info-icon">ⓘ</span>
          </el-tooltip>
        </div>

        <!-- 资产统计 -->
        <div v-if="store.currentConfigId" class="assets-stats">
          <div class="stat-item">
            <span class="stat-label">区域:</span>
            <span class="stat-value">{{ assetsStats.zoneCount }}</span>
          </div>
          <div class="stat-item">
            <span class="stat-label">机器:</span>
            <span class="stat-value">{{ assetsStats.machineCount }}</span>
          </div>
          <div class="stat-item">
            <span class="stat-label">路由点:</span>
            <span class="stat-value">{{ assetsStats.waypointCount }}</span>
          </div>
          <div class="stat-item">
            <span class="stat-label">总计:</span>
            <span class="stat-value">{{ assetsStats.totalAssets }}</span>
          </div>
        </div>

        <!-- 资产列表 -->
        <div class="services-list-container">
          <div v-if="assetsList.length === 0" class="empty-state">
            <div class="empty-icon">📦</div>
            <p>请先选择或上传配置文件</p>
          </div>
          <ul v-else class="services-list">
            <li
              v-for="(asset, index) in assetsList"
              :key="index"
              class="service-item"
              :class="`asset-type-${asset.type}`"
            >
              <el-tooltip placement="left" :open-delay="500" effect="dark">
                <template #content>
                  <div class="tooltip-content">{{ asset.description }}</div>
                </template>
                <div
                  class="draggable-node"
                  draggable="true"
                  @dragstart="onDragStart($event, asset)"
                >
                  <span class="node-icon">{{ asset.icon }}</span>
                  <span class="node-name">{{ asset.name }}</span>
                  <span class="drag-handle">⋮⋮</span>
                </div>
              </el-tooltip>
            </li>
          </ul>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { ElMessage } from 'element-plus'
import { useFactoryStore } from '@/stores/factory'
import { validateAndNormalizeConfig } from '@/utils/configValidator'
import { apiPost, API_ROUTES } from '@/utils/api'

// --- Store ---
const store = useFactoryStore()

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

// --- Computed ---
const loadedConfigs = computed(() => {
  return Object.values(store.factoryConfigs || {})
})

const currentConfigId = computed(() => store.currentConfigId)

// 动态生成工厂资产列表（根据当前选中的配置）
const assetsList = computed(() => {
  if (!store.currentConfigId) {
    return []
  }
  return store.formatAssetsList()
})

// 资产统计信息
const assetsStats = computed(() => {
  return store.getAssetsStats()
})

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

function selectConfig(configId) {
  store.setCurrentConfig(configId)
  ElMessage.success('已切换配置')
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

/**
 * 暴露给父组件的方法
 */
function getSelectedFile() {
  return selectedFile.value
}

// --- Drag Logic ---
const onDragStart = (event, service) => {
  event.dataTransfer.setData('application/node-data', JSON.stringify(service))
  event.dataTransfer.effectAllowed = 'copy'
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
