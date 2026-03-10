<template>
  <div class="control-panel-container">
    <div class="panel-header">
      <h2>⚙️ 控制面板</h2>
    </div>

    <div class="control-section">
      <h3>播放控制</h3>
      <button class="play-btn" :class="{ playing: store.isPlaying }" @click="store.togglePlay">
        {{ store.isPlaying ? '⏸ 暂停' : '▶ 播放' }}
      </button>
      <button class="reset-btn" @click="store.reset">↻ 重置</button>
    </div>

    <div class="control-section">
      <h3>时间轴</h3>
      <div class="timeline-info-top">
        <span class="label">当前步数</span>
        <span class="value">{{ store.currentIndex }} / {{ store.totalSteps }}</span>
      </div>
      <div class="slider-container">
        <input
          :value="store.currentIndex"
          @input="(e) => store.setIndex(e.target.value)"
          type="range"
          :min="0"
          :max="store.totalSteps > 0 ? store.totalSteps - 1 : 0"
          class="timeline-slider"
          :disabled="store.totalSteps === 0"
        />
      </div>
      <div class="timeline-progress">
        <span>{{ progressPercentage }}%</span>
      </div>
    </div>

    <div class="control-section">
      <h3>📊 实时状态</h3>

      <div class="info-item">
        <span class="label">时间步:</span>
        <span class="value highlight">{{ store.currentState?.env_timeline || '-' }}</span>
      </div>

      <div class="info-item">
        <span class="label">活跃 AGV:</span>
        <span class="value">{{ activeAGVCount }} / {{ totalAGVCount }}</span>
      </div>

      <div class="info-item">
        <span class="label">总机器:</span>
        <span class="value">{{ totalMachineCount }}</span>
      </div>

      <div class="info-item">
        <span class="label">工作中:</span>
        <span class="value working">{{ workingMachineCount }}</span>
      </div>

      <div class="info-item">
        <span class="label">未工作:</span>
        <span class="value idle" :style="{ color: idleMachineCount > 0 ? '#4CAF50' : '#999' }">
          {{ idleMachineCount }}
        </span>
      </div>

      <div class="info-item">
        <span class="label">活跃任务:</span>
        <span class="value transfer">{{ activeTransferCount }}</span>
      </div>
    </div>

    <div class="control-section">
      <h3>🎬 动画配置</h3>

      <div class="info-item">
        <span class="label">动画模式:</span>
        <span class="value" :style="{ color: '#667eea' }">
          {{ animationMode }}
        </span>
      </div>

      <div class="info-item">
        <span class="label">插值状态:</span>
        <span class="value">
          {{ isAnimating ? '✨ 启用' : '⏸ 等待' }}
        </span>
      </div>

      <div class="info-item">
        <span class="label">呼吸效果:</span>
        <span class="value">✓ 启用</span>
      </div>
    </div>

    <div class="panel-footer">
      <p>Factory Visualization System</p>
      <p class="version">v2.0.1 LTS</p>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useFactoryStore } from '@/stores/factory'

// 1. 初始化 Store
const store = useFactoryStore()

// 2. 将原本基于 props 的计算属性改为基于 store.currentState
const activeAGVCount = computed(() => {
  const { grid_state } = store.currentState
  if (!grid_state) return 0
  const { is_active = [] } = grid_state
  return Array.isArray(is_active) ? is_active.filter(Boolean).length : 0
})

const totalAGVCount = computed(() => {
  const { grid_state } = store.currentState
  return grid_state?.positions_xy?.length || 0
})

const workingMachineCount = computed(() => {
  const machines = store.currentState?.machines || []
  // 兼容 machines 可能是对象或数组的情况
  const list = Array.isArray(machines) ? machines : Object.values(machines)
  return list.filter((m) => m.status === 'WORKING').length
})

const totalMachineCount = computed(() => {
  // 【关键】从当前配置的拓扑读取总机器数
  // 这样才能获得配置文件中的所有机器，而不受 fullSystemTest 推送的状态限制
  const config = store.currentConfig
  if (!config || !config.topology) {
    return 0
  }
  const staticMachines = config.topology.machines || {}
  return Object.keys(staticMachines).length
})

const idleMachineCount = computed(() => {
  // 未工作 = 总数 - 工作中的数量
  return Math.max(0, totalMachineCount.value - workingMachineCount.value)
})

const activeTransferCount = computed(() => {
  return store.currentState?.active_transfers?.length || 0
})

// UI 辅助计算属性
const progressPercentage = computed(() => {
  if (store.totalSteps <= 1) return 0
  return Math.round((store.currentIndex / (store.totalSteps - 1)) * 100)
})

const isAnimating = computed(() => store.isPlaying)

const animationMode = computed(() => (store.isPlaying ? '游戏循环 + Lerp' : '等待中'))
</script>

<style scoped>
@import './styles/ControlPanel.css';
</style>
