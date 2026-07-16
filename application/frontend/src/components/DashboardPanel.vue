<template>
  <div class="dashboard-panel">
    <div class="dashboard-head">
      <h3>{{ config.title || '实时看板' }}</h3>
      <div class="dashboard-actions">
        <button
          class="icon-btn"
          title="导出当前会话为 JSON"
          @click="handleExportLive"
        >⬇</button>
        <span class="step-tag" v-if="lastStep != null">step {{ lastStep }}</span>
      </div>
    </div>

    <div class="dashboard-cards" :class="`layout-${config.layout || 'grid-2col'}`">
      <div
        v-for="card in config.cards"
        :key="card.hook + card.template"
        class="dashboard-card"
      >
        <div class="card-head">
          <span class="card-title">{{ card.title || hookLabel(card.hook) }}</span>
          <span class="card-unit" v-if="card.unit">unit: {{ card.unit }}</span>
        </div>
        <component
          :is="resolveTemplate(card.template)"
          :series="safeSeries(card)"
          :y-label="card.unit || ''"
          :y-max="card.yMax || null"
          :mode="card.mode || 'grouped'"
          :height="card.height || '220px'"
          :show-data-zoom="false"
        />
      </div>
    </div>

    <div v-if="!hasAnyData" class="dashboard-empty">
      <span>暂无指标数据（请先启动仿真）</span>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useMonitorStore } from '@/stores/monitor'
import { useFactoryStore } from '@/stores/factory'
import { useAnalysisLogStore } from '@/stores/analysisLog'
import { getHook } from '@/hooks/metrics'
import { getTemplate } from '@/components/charts'
import { ElMessage } from 'element-plus'

const props = defineProps({
  config: { type: Object, required: true },
})

const monitorStore = useMonitorStore()
const factoryStore = useFactoryStore()
const analysisLog = useAnalysisLogStore()
const MAX_TREND_POINTS = 72

// 归一化 ctx —— 实时模式 source=live，数据来自 monitorStore
const ctx = computed(() => ({
  metrics: monitorStore.metricsTimeline,
  frames: factoryStore.historyBuffer,
  events: monitorStore.events,
  source: 'live',
}))

const lastStep = computed(() => {
  const tl = monitorStore.metricsTimeline
  if (!tl || tl.length === 0) return null
  const last = tl[tl.length - 1]
  return last?.step ?? tl.length - 1
})

function resolveTemplate(name) {
  const t = getTemplate(name)
  if (!t) {
    console.warn(`[DashboardPanel] unknown template: ${name}`)
  }
  return t
}

function hookLabel(hookId) {
  return getHook(hookId)?.label || hookId
}

function compactSeries(series, aggregation = 'mean') {
  const data = series?.data || []
  if (data.length <= MAX_TREND_POINTS) return series

  const pointCount = Math.min(MAX_TREND_POINTS, data.length)
  const compacted = []
  for (let bucket = 0; bucket < pointCount; bucket += 1) {
    const start = Math.floor((bucket * data.length) / pointCount)
    const end = Math.floor(((bucket + 1) * data.length) / pointCount)
    const points = data.slice(start, Math.max(start + 1, end))
    const last = points[points.length - 1]
    const values = points.map((point) => point.y).filter(Number.isFinite)
    if (!last || values.length === 0) continue
    const y = aggregation === 'last'
      ? last.y
      : values.reduce((sum, value) => sum + value, 0) / values.length
    compacted.push({ x: last.x, y: Number(y.toFixed(2)) })
  }
  return { ...series, data: compacted }
}

function safeSeries(card) {
  const hook = getHook(card.hook)
  if (!hook) {
    console.warn(`[DashboardPanel] unknown hook: ${card.hook}`)
    return []
  }
  try {
    const r = hook.series(ctx.value)
    if (!Array.isArray(r) || card.template !== 'line') return Array.isArray(r) ? r : []
    return r.map((series) => compactSeries(series, card.aggregation || 'mean'))
  } catch (e) {
    console.warn(`[DashboardPanel] hook ${card.hook} error:`, e)
    return []
  }
}

const hasAnyData = computed(() => {
  if (!props.config.cards) return false
  return props.config.cards.some((card) => {
    const s = safeSeries(card)
    return s.some((series) => Array.isArray(series?.data) && series.data.length > 0)
  })
})

async function handleExportLive() {
  try {
    await analysisLog.exportLive(factoryStore, monitorStore, {
      factory_id: factoryStore.selectedFactoryId,
    })
    ElMessage.success('已导出当前会话')
  } catch (e) {
    console.error('[DashboardPanel] exportLive failed:', e)
    ElMessage.error('导出失败')
  }
}
</script>

<style scoped>
.dashboard-panel {
  display: flex;
  flex-direction: column;
  gap: 10px;
  padding: 6px 4px;
  height: 100%;
  min-height: 0;
  color: rgba(220, 230, 245, 0.9);
}

.dashboard-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 4px 8px;
  border-bottom: 1px dashed rgba(100, 180, 255, 0.1);
  flex-shrink: 0;
}

.dashboard-head h3 {
  margin: 0;
  font-size: 13px;
  font-weight: 600;
  color: rgba(220, 230, 245, 0.95);
}

.dashboard-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.icon-btn {
  background: rgba(100, 180, 255, 0.08);
  border: 1px solid rgba(100, 180, 255, 0.15);
  color: rgba(160, 190, 230, 0.6);
  width: 22px;
  height: 22px;
  border-radius: 4px;
  font-size: 12px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.15s;
}

.icon-btn:hover {
  background: rgba(100, 180, 255, 0.18);
  color: rgba(220, 230, 245, 1);
}

.step-tag {
  font-size: 10px;
  color: rgba(100, 180, 255, 0.7);
  background: rgba(100, 180, 255, 0.08);
  padding: 1px 8px;
  border-radius: 8px;
  font-variant-numeric: tabular-nums;
}

.dashboard-cards {
  flex: 1;
  overflow-y: auto;
  display: grid;
  gap: 8px;
  align-content: start;
  padding: 2px 4px;
}

.layout-grid-2col {
  grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
}

.dashboard-cards::-webkit-scrollbar {
  width: 4px;
}
.dashboard-cards::-webkit-scrollbar-thumb {
  background: rgba(100, 180, 255, 0.15);
  border-radius: 2px;
}

.dashboard-card {
  background: rgba(20, 26, 48, 0.5);
  border: 1px solid rgba(100, 180, 255, 0.1);
  border-radius: 8px;
  padding: 8px 10px;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.card-head {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
}

.card-title {
  font-size: 12px;
  font-weight: 600;
  color: rgba(220, 230, 245, 0.9);
}

.card-unit {
  font-size: 9px;
  color: rgba(160, 190, 230, 0.4);
}

.dashboard-empty {
  text-align: center;
  font-size: 12px;
  color: rgba(160, 190, 230, 0.3);
  padding: 40px 0;
}
</style>
