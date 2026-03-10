<template>
  <div class="home">
    <div class="bg-overlay"></div>

    <div class="home-container">
      <div class="home-header">
        <div class="logo-area">
          <h1 class="glitch-text" data-text="TianGong">TianGong</h1>
          <div class="version-badge">VER 2.0</div>
        </div>
        <p class="subtitle">天工数字孪生算力底座</p>
        <div class="deco-line"></div>
      </div>

      <div class="home-cards">
        <div class="card main-card" @click="navigateToFactory">
          <div class="card-glow"></div>
          <div class="card-content">
            <div class="icon-wrapper">
              <span class="icon">🏭</span>
            </div>
            <h2>数字车间</h2>
            <p class="en-text">Digital Factory Workspace</p>
            <p class="desc">进入工厂可视化管理，实时监控与资源配置。</p>
            <button class="btn-entry">
              立即接入
              <span class="arrow">→</span>
            </button>
          </div>
        </div>

        <div class="card info-card">
          <div class="card-content">
            <div class="icon-wrapper secondary">
              <span class="icon">📡</span>
            </div>
            <h2>系统状态</h2>
            <p class="en-text">System Status</p>

            <div class="status-list">
              <div class="status-item">
                <span class="label">当前版本</span>
                <span class="value">2.0.1 LTS</span>
              </div>
              <div class="status-item">
                <span class="label">运行模式</span>
                <span class="value success">Lite / Local</span>
              </div>
              <div class="status-item">
                <span class="label">后端活性</span>
                <span
                  class="value"
                  :class="backendStatus === null ? 'warning' : backendStatus ? 'success' : 'error'"
                  >{{
                    backendStatus === null ? '检测中...' : backendStatus ? '在线' : '离线'
                  }}</span
                >
              </div>
              <div class="status-item">
                <span class="label">真实场景</span>
                <span
                  class="value"
                  :class="
                    scenarioConnected === null ? 'warning' : scenarioConnected ? 'success' : 'error'
                  "
                  >{{
                    scenarioConnected === null
                      ? '检测中...'
                      : scenarioConnected
                        ? '已连接'
                        : '未连接'
                  }}</span
                >
              </div>
            </div>
          </div>
        </div>
      </div>

      <div class="footer">&copy; 2025 TianGong Industrial. All rights reserved.</div>
    </div>
  </div>
</template>

<script setup>
import { useRouter } from 'vue-router'
import { ref, onMounted, onBeforeUnmount } from 'vue'
import { apiGet, API_ROUTES } from '../utils/api'
import './styles/HomeView.scss'

const router = useRouter()
const backendStatus = ref(null)
const scenarioConnected = ref(null)

// 重试配置
const retryConfig = {
  maxRetries: 5, // 最大重试次数
  initialDelay: 1000, // 初始延迟 1秒
  maxDelay: 30000, // 最大延迟 30秒
}

let backendRetries = 0
let scenarioRetries = 0
let backendTimeoutId = null
let scenarioTimeoutId = null

const navigateToFactory = () => {
  router.push('/factory')
}

// 计算指数退避延迟
const getRetryDelay = (retryCount) => {
  const delay = Math.min(retryConfig.initialDelay * Math.pow(2, retryCount), retryConfig.maxDelay)
  // 添加随机抖动（±20%）
  const jitter = delay * 0.2 * (Math.random() - 0.5)
  return Math.max(delay + jitter, retryConfig.initialDelay)
}

// 检查后端状态，失败时自动重试
const checkBackendStatus = async () => {
  try {
    const response = await apiGet(API_ROUTES.HEALTH)
    // 检查是否真的收到了成功的响应
    if (response && response.status === 'ok') {
      backendStatus.value = true
      backendRetries = 0 // 成功后重置重试计数
    } else {
      throw new Error('Invalid health check response')
    }
  } catch (error) {
    backendStatus.value = false

    // 如果未达到最大重试次数，安排重试
    if (backendRetries < retryConfig.maxRetries) {
      const delay = getRetryDelay(backendRetries)
      backendRetries++
      console.log(
        `[HomeView] 后端检查失败，${(delay / 1000).toFixed(1)}秒后重试 (${backendRetries}/${retryConfig.maxRetries})`,
      )

      backendTimeoutId = setTimeout(() => {
        checkBackendStatus()
      }, delay)
    } else {
      console.warn('[HomeView] 后端已达到最大重试次数，停止重试')
    }
  }
}

// 检查场景连接，失败时自动重试
const checkScenarioConnection = async () => {
  try {
    const response = await apiGet(API_ROUTES.SCENARIO_STATUS)
    // 检查是否真的收到了成功的响应
    if (response && response.scenario === 'ok') {
      scenarioConnected.value = true
      scenarioRetries = 0 // 成功后重置重试计数
    } else {
      throw new Error('Invalid scenario status response')
    }
  } catch (error) {
    scenarioConnected.value = false

    // 如果未达到最大重试次数，安排重试
    if (scenarioRetries < retryConfig.maxRetries) {
      const delay = getRetryDelay(scenarioRetries)
      scenarioRetries++
      console.log(
        `[HomeView] 场景检查失败，${(delay / 1000).toFixed(1)}秒后重试 (${scenarioRetries}/${retryConfig.maxRetries})`,
      )

      scenarioTimeoutId = setTimeout(() => {
        checkScenarioConnection()
      }, delay)
    } else {
      console.warn('[HomeView] 场景已达到最大重试次数，停止重试')
    }
  }
}

// 清理定时器
const clearRetryTimers = () => {
  if (backendTimeoutId) {
    clearTimeout(backendTimeoutId)
  }
  if (scenarioTimeoutId) {
    clearTimeout(scenarioTimeoutId)
  }
}

onMounted(() => {
  checkBackendStatus()
  checkScenarioConnection()
})

// 组件卸载时清理定时器
onBeforeUnmount(() => {
  clearRetryTimers()
})
</script>
<style scoped>
@import './styles/HomeView.scss';
</style>
