<template>
  <DraggablePanel
    :icon="currentView === 'detail' ? '📦' : '📋'"
    :title="currentView === 'detail' ? '离线分析 · 详情' : '离线分析样本'"
    :width="760"
    :height="560"
    :initial-pos="{ x: 280, y: 80 }"
    :collapsible="false"
    @close="$emit('close')"
  >
    <div class="analysis-overlay">
      <!-- ============ 列表视图 ============ -->
      <template v-if="currentView === 'list'">
        <div class="ao-header">
          <span class="ao-count">
            共 {{ analysisLog.totalRuns }} 条
            <span v-if="analysisLog.loading" class="ao-loading-hint">（加载中…）</span>
          </span>
          <div class="ao-header-actions">
            <button class="ao-btn ghost" title="刷新列表" @click="analysisLog.listRuns()">↻</button>
            <button class="ao-btn primary" @click="handleUploadLog">⬆ 上传日志分析</button>
            <input ref="fileInputRef" type="file" accept=".json,application/json" hidden @change="onFilePicked" />
          </div>
        </div>

        <div v-if="analysisLog.error" class="ao-error-banner">
          ⚠ 列表加载失败：{{ analysisLog.error }}
          <button class="ao-btn ghost small" @click="analysisLog.listRuns()">重试</button>
        </div>

        <div v-if="!analysisLog.loading && analysisLog.totalRuns === 0 && !analysisLog.error" class="ao-empty">
          <div class="ao-empty-icon">📊</div>
          <p>暂无分析样本</p>
          <span class="ao-empty-hint">跑一次仿真，episode 结束后会自动保存到此处</span>
        </div>

        <div v-else class="ao-run-list">
          <div
            v-for="run in analysisLog.runs"
            :key="run.id"
            class="ao-run-card"
            :class="{ imported: run.source === 'imported' }"
            @click="openDetail(run.id)"
          >
            <div class="ao-run-head">
              <span class="ao-run-id" :title="run.id">
                {{ run.source === 'imported' ? '📁' : '📦' }} {{ run.id }}
              </span>
              <span v-if="run.source === 'imported'" class="ao-tag imported-tag" title="用户上传的样本">导入</span>
              <span class="ao-tag factory" :title="run.factory_id">{{ run.factory_id }}</span>
              <span v-if="run.algorithm" class="ao-tag algo" :title="run.algorithm">{{ run.algorithm }}</span>
              <button class="ao-icon-btn" title="下载 JSON" @click.stop="handleExport(run.id)">⬇</button>
              <button class="ao-icon-btn danger" title="删除" @click.stop="handleDelete(run.id)">×</button>
            </div>
            <div class="ao-run-meta">
              <div class="ao-meta-item">
                <span class="ao-meta-label">总步数</span>
                <span class="ao-meta-value">{{ run.summary?.total_steps ?? '--' }}</span>
              </div>
              <div class="ao-meta-item">
                <span class="ao-meta-label">Job 完成</span>
                <span class="ao-meta-value">{{ run.summary?.completed_jobs ?? 0 }}/{{ run.summary?.total_jobs ?? 0 }}</span>
              </div>
              <div class="ao-meta-item">
                <span class="ao-meta-label">事件总数</span>
                <span class="ao-meta-value">{{ run.summary?.event_total ?? 0 }}</span>
              </div>
              <div class="ao-meta-item" v-if="run.summary?.avg_utilization != null">
                <span class="ao-meta-label">平均利用率</span>
                <span class="ao-meta-value">{{ (run.summary.avg_utilization * 100).toFixed(1) }}%</span>
              </div>
            </div>
            <div class="ao-run-footer">
              <span class="ao-created">
                {{ formatTime(run.created_at) }}
                <span v-if="run.source === 'imported' && run.original_filename" class="ao-original-name" :title="run.original_filename">· 来源：{{ run.original_filename }}</span>
              </span>
              <span class="ao-view-link">查看详情 →</span>
            </div>
          </div>
        </div>
      </template>

      <!-- ============ 详情视图 ============ -->
      <template v-else>
        <div v-if="analysisLog.detailLoading && !currentRun" class="ao-empty">
          <div class="ao-empty-icon">⏳</div>
          <p>加载中…</p>
        </div>

        <div v-else-if="!currentRun" class="ao-empty">
          <div class="ao-empty-icon">📭</div>
          <p v-if="detailError">加载失败</p>
          <p v-else>该样本不存在或已被删除</p>
          <span v-if="detailError" class="ao-empty-hint" style="color: rgba(255,150,150,0.8); margin-bottom: 8px;">{{ detailError }}</span>
          <div style="display: flex; gap: 6px;">
            <button class="ao-btn ghost" @click="backToList">返回列表</button>
            <button v-if="detailError" class="ao-btn ghost" @click="openDetail(currentRunId)">重试</button>
          </div>
        </div>

        <template v-else>
          <div class="ao-detail-header">
            <button class="ao-btn ghost" @click="backToList">← 返回列表</button>
            <span class="ao-run-id" :title="currentRun.id">
              {{ currentRun.source === 'imported' ? '📁' : '📦' }} {{ currentRun.id }}
            </span>
            <span v-if="currentRun.source === 'imported'" class="ao-tag imported-tag">导入</span>
            <span class="ao-tag factory">{{ currentRun.factory_id }}</span>
            <span v-if="currentRun.algorithm" class="ao-tag algo">{{ currentRun.algorithm }}</span>
            <span class="ao-tag time">{{ formatTime(currentRun.created_at) }}</span>
          </div>

          <div class="ao-summary-grid">
            <div class="ao-summary-card">
              <div class="ao-summary-label">总步数</div>
              <div class="ao-summary-value">{{ currentRun.summary?.total_steps ?? '--' }}</div>
            </div>
            <div class="ao-summary-card">
              <div class="ao-summary-label">Job 完成</div>
              <div class="ao-summary-value">{{ currentRun.summary?.completed_jobs ?? 0 }}/{{ currentRun.summary?.total_jobs ?? 0 }}</div>
            </div>
            <div class="ao-summary-card">
              <div class="ao-summary-label">事件总数</div>
              <div class="ao-summary-value">{{ currentRun.summary?.event_total ?? 0 }}</div>
            </div>
            <div class="ao-summary-card" v-if="currentRun.summary?.avg_utilization != null">
              <div class="ao-summary-label">平均利用率</div>
              <div class="ao-summary-value">{{ (currentRun.summary.avg_utilization * 100).toFixed(1) }}%</div>
            </div>
          </div>

          <div v-if="hasChartData" class="ao-charts-grid">
            <div v-for="hook in hooks" :key="hook.id" class="ao-chart-card">
              <div class="ao-chart-head">
                <span class="ao-chart-title">{{ hook.label }}</span>
                <span v-if="hook.unit" class="ao-chart-unit">unit: {{ hook.unit }}</span>
              </div>
              <LineChart
                :series="safeSeries(hook)"
                :y-label="hook.unit || ''"
                height="200px"
              />
            </div>
          </div>

          <div v-else class="ao-data-empty">
            该样本没有可绘制的时序数据，下面展示已归档的摘要和事件。
          </div>

          <div class="ao-detail-data-grid">
            <div class="ao-data-card">
              <div class="ao-data-title">摘要字段</div>
              <div v-if="summaryEntries.length === 0" class="ao-data-empty small">暂无摘要字段</div>
              <div v-for="item in summaryEntries" :key="item.key" class="ao-data-row">
                <span>{{ item.key }}</span>
                <code>{{ item.value }}</code>
              </div>
            </div>
            <div class="ao-data-card">
              <div class="ao-data-title">日志事件</div>
              <div v-if="detailEvents.length === 0" class="ao-data-empty small">暂无事件数据</div>
              <div v-for="event in detailEvents" :key="event.id || `${event.type}-${event.step}-${event.idx}`" class="ao-event-row">
                <div class="ao-event-main">
                  <span class="ao-event-step">#{{ event.step ?? event.idx ?? '--' }}</span>
                  <span class="ao-event-title">{{ event.title || event.type || 'event' }}</span>
                </div>
                <div v-if="event.message" class="ao-event-message">{{ event.message }}</div>
                <pre v-if="event.payload && Object.keys(event.payload || {}).length" class="ao-event-payload">{{ formatJson(event.payload) }}</pre>
              </div>
            </div>
          </div>
        </template>
      </template>
    </div>
  </DraggablePanel>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { ElMessageBox, ElMessage } from 'element-plus'
import DraggablePanel from '@/components/DraggablePanel.vue'
import LineChart from '@/components/charts/LineChart.vue'
import { useAnalysisLogStore } from '@/stores/analysisLog'
import { listHooks } from '@/hooks/metrics'

defineEmits(['close'])

const analysisLog = useAnalysisLogStore()
const hooks = listHooks()

// 当前查看的 runId；null = 列表视图
const currentRunId = ref(null)
const currentView = computed(() => (currentRunId.value ? 'detail' : 'list'))
// 详情优先用 currentDetail（按需加载的完整 Run，含三流）
// 列表条目（runs[]）只有元信息，不能直接喂 Hook
const currentRun = computed(() => {
  if (!currentRunId.value) return null
  if (analysisLog.currentDetail?.id === currentRunId.value) return analysisLog.currentDetail
  return null
})

const hasChartData = computed(() => {
  if (!currentRun.value) return false
  return (
    (currentRun.value.metricsTimeline || []).length > 0 ||
    (currentRun.value.frames || []).length > 1
  )
})

const detailEvents = computed(() => (currentRun.value?.events || []).slice(0, 200))

const summaryEntries = computed(() => {
  const summary = currentRun.value?.summary || {}
  return Object.entries(summary).map(([key, value]) => ({
    key,
    value: typeof value === 'object' ? JSON.stringify(value) : String(value),
  }))
})

// 进入详情视图：按需加载完整 Run
// 显式处理失败：不依赖 watch（currentRun null→null 不触发 watch 的缺陷）
const detailError = ref(null)

async function openDetail(id) {
  currentRunId.value = id
  detailError.value = null
  const run = await analysisLog.loadRun(id)
  if (!run && currentRunId.value === id) {
    // loadRun 失败（HTTP 错误 / 404 / 网络问题）
    detailError.value = analysisLog.error || '加载失败：样本可能不存在或网络错误'
  }
}
function backToList() {
  currentRunId.value = null
  detailError.value = null
  analysisLog.currentDetail = null
}

// 挂载时若 store 指定了 initialRunId（从 EventPanel 历史样本点进来），直接进详情
watch(
  () => analysisLog.initialRunId,
  async (id) => {
    if (id) {
      currentRunId.value = id
      detailError.value = null
      analysisLog.initialRunId = null
      const run = await analysisLog.loadRun(id)
      if (!run && currentRunId.value === id) {
        detailError.value = analysisLog.error || '加载失败'
      }
    }
  },
  { immediate: true }
)

// 详情被删时退回列表（currentRun 从有值变 null 时才触发，覆盖删除场景）
watch(currentRun, (r) => {
  if (currentRunId.value && !r && !analysisLog.detailLoading && !detailError.value) {
    currentRunId.value = null
  }
})

const ctx = computed(() => {
  if (!currentRun.value) return { metrics: [], frames: [], events: [], source: 'archive' }
  return {
    metrics: currentRun.value.metricsTimeline || [],
    frames: currentRun.value.frames || [],
    events: currentRun.value.events || [],
    source: currentRun.value.source || 'archive',
  }
})

function safeSeries(hook) {
  try {
    const r = hook.series(ctx.value)
    return Array.isArray(r) ? r : []
  } catch (e) {
    console.warn('[AnalysisOverlay] hook error:', hook.id, e)
    return []
  }
}

function formatTime(iso) {
  if (!iso) return ''
  const d = new Date(iso)
  const pad = (n) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ` +
         `${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`
}

function formatJson(value) {
  try {
    return JSON.stringify(value, null, 2)
  } catch {
    return String(value)
  }
}

async function handleExport(id) {
  const ok = await analysisLog.exportRun(id)
  if (ok) ElMessage.success('已下载')
  else ElMessage.error('样本不存在或下载失败')
}

// ============ 上传日志分析 ============
const fileInputRef = ref(null)

function handleUploadLog() {
  fileInputRef.value?.click()
}

async function onFilePicked(e) {
  const file = e.target.files?.[0]
  if (!file) return
  try {
    const text = await file.text()
    let payload
    try {
      payload = JSON.parse(text)
    } catch (parseErr) {
      throw new Error('JSON 格式无效')
    }
    const run = await analysisLog.importRun(payload, file.name)
    ElMessage.success(`已导入：${run.id}`)
    await openDetail(run.id)
  } catch (err) {
    console.warn('[AnalysisOverlay] importRun failed:', err)
    ElMessage.error(`导入失败：${err.message || err}`)
  } finally {
    e.target.value = ''  // 允许重选同一个文件
  }
}

function handleDelete(id) {
  ElMessageBox.confirm('确定删除这条样本？删除后无法恢复。', '删除确认', {
    type: 'warning', confirmButtonText: '删除', cancelButtonText: '取消',
  })
    .then(() => {
      analysisLog.deleteRun(id)
      ElMessage.success('已删除')
    })
    .catch(() => {})
}
</script>

<style scoped>
.analysis-overlay {
  --ao-fg: rgba(220, 230, 245, 0.9);
  --ao-fg-dim: rgba(160, 190, 230, 0.5);
  --ao-accent: rgba(100, 180, 255, 0.8);
  --ao-border: rgba(100, 180, 255, 0.15);
  --ao-bg: rgba(20, 26, 48, 0.6);
  color: var(--ao-fg);
  font-size: 12px;
  display: flex;
  flex-direction: column;
  height: 100%;
  overflow-y: auto;
}

.ao-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 6px 4px 10px;
  border-bottom: 1px dashed var(--ao-border);
  margin-bottom: 10px;
}
.ao-count { font-size: 11px; color: var(--ao-fg-dim); }
.ao-loading-hint { color: var(--ao-accent); margin-left: 4px; }
.ao-header-actions { display: flex; gap: 6px; }

.ao-error-banner {
  background: rgba(255, 100, 100, 0.08);
  border: 1px solid rgba(255, 100, 100, 0.25);
  border-radius: 6px;
  padding: 6px 10px;
  margin-bottom: 10px;
  font-size: 11px;
  color: rgba(255, 180, 180, 0.9);
  display: flex;
  align-items: center;
  gap: 8px;
}
.ao-btn.small { padding: 2px 8px; font-size: 10px; }
.ao-btn.ghost.small { background: transparent; border-color: rgba(255, 150, 150, 0.3); }

.ao-btn {
  padding: 4px 10px;
  border-radius: 6px;
  font-size: 11px;
  cursor: pointer;
  border: 1px solid var(--ao-border);
  background: rgba(100, 180, 255, 0.08);
  color: rgba(200, 220, 255, 0.85);
}
.ao-btn:hover { background: rgba(100, 180, 255, 0.18); }
.ao-btn.ghost { background: transparent; }
.ao-btn.primary {
  background: rgba(100, 180, 255, 0.18);
  border-color: rgba(100, 180, 255, 0.4);
  color: rgba(220, 230, 245, 0.95);
}
.ao-btn:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}
.ao-btn:disabled:hover { background: rgba(100, 180, 255, 0.08); }
.ao-btn.danger {
  background: rgba(255, 100, 100, 0.08);
  border-color: rgba(255, 100, 100, 0.25);
  color: rgba(255, 150, 150, 0.9);
}
.ao-btn.danger:hover { background: rgba(255, 100, 100, 0.18); }

.ao-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 40px 16px;
  text-align: center;
}
.ao-empty-icon { font-size: 40px; opacity: 0.5; margin-bottom: 10px; }
.ao-empty p { margin: 0 0 4px; font-size: 13px; color: rgba(220, 230, 245, 0.8); }
.ao-empty-hint { font-size: 11px; color: var(--ao-fg-dim); }

.ao-data-empty {
  padding: 10px 12px;
  border: 1px dashed var(--ao-border);
  border-radius: 7px;
  color: var(--ao-fg-dim);
  background: rgba(100, 180, 255, 0.035);
  font-size: 11px;
  margin-bottom: 10px;
}
.ao-data-empty.small {
  padding: 8px;
  margin: 0;
  text-align: center;
}

.ao-detail-data-grid {
  display: grid;
  grid-template-columns: minmax(220px, 0.8fr) minmax(320px, 1.2fr);
  gap: 10px;
  margin-top: 10px;
}

.ao-data-card {
  min-width: 0;
  background: var(--ao-bg);
  border: 1px solid var(--ao-border);
  border-radius: 8px;
  padding: 10px;
}

.ao-data-title {
  font-size: 12px;
  font-weight: 700;
  color: rgba(220, 230, 245, 0.9);
  margin-bottom: 8px;
}

.ao-data-row {
  display: flex;
  justify-content: space-between;
  gap: 10px;
  padding: 5px 0;
  border-bottom: 1px solid rgba(100, 180, 255, 0.08);
  color: var(--ao-fg-dim);
}

.ao-data-row code {
  color: var(--ao-fg);
  font-family: 'Consolas', 'Monaco', monospace;
  text-align: right;
  overflow-wrap: anywhere;
}

.ao-event-row {
  padding: 7px 0;
  border-bottom: 1px solid rgba(100, 180, 255, 0.08);
}

.ao-event-main {
  display: flex;
  gap: 8px;
  align-items: center;
}

.ao-event-step {
  font-family: 'Consolas', 'Monaco', monospace;
  color: rgba(100, 180, 255, 0.75);
  font-size: 10px;
}

.ao-event-title {
  color: rgba(220, 230, 245, 0.88);
  font-weight: 600;
}

.ao-event-message {
  margin-top: 3px;
  color: var(--ao-fg-dim);
  font-size: 11px;
}

.ao-event-payload {
  margin: 6px 0 0;
  max-height: 140px;
  overflow: auto;
  white-space: pre-wrap;
  color: rgba(220, 230, 245, 0.78);
  font-family: 'Consolas', 'Monaco', monospace;
  font-size: 10px;
  line-height: 1.35;
  background: rgba(5, 10, 20, 0.25);
  border-radius: 5px;
  padding: 6px;
}

.ao-run-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.ao-run-card {
  background: var(--ao-bg);
  border: 1px solid var(--ao-border);
  border-radius: 8px;
  padding: 10px 12px;
  cursor: pointer;
  transition: border-color 0.15s, background 0.15s;
}
.ao-run-card:hover {
  border-color: rgba(100, 180, 255, 0.4);
  background: rgba(20, 26, 48, 0.85);
}
.ao-run-head {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 8px;
  min-width: 0;
}
.ao-run-id {
  font-size: 12px;
  font-weight: 700;
  color: rgba(240, 245, 255, 1);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  flex: 1 1 auto;
  min-width: 0;
}
.ao-tag {
  font-size: 10px;
  padding: 2px 7px;
  border-radius: 8px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  max-width: 120px;
  flex-shrink: 0;
}
.ao-tag.factory { background: rgba(100, 180, 255, 0.12); color: rgba(180, 220, 255, 0.9); }
.ao-tag.algo { background: rgba(102, 208, 106, 0.12); color: rgba(150, 230, 160, 0.9); }
.ao-tag.time { background: rgba(255, 255, 255, 0.04); color: var(--ao-fg-dim); font-variant-numeric: tabular-nums; }
.ao-tag.imported-tag {
  background: rgba(178, 100, 255, 0.14);
  color: rgba(200, 160, 255, 0.95);
  border: 1px solid rgba(178, 100, 255, 0.25);
}
.ao-run-card.imported { border-color: rgba(178, 100, 255, 0.18); }
.ao-run-card.imported:hover { border-color: rgba(178, 100, 255, 0.4); }

.ao-original-name { color: var(--ao-fg-dim); opacity: 0.7; }

.ao-icon-btn {
  background: none;
  border: none;
  color: var(--ao-fg-dim);
  font-size: 13px;
  cursor: pointer;
  padding: 0 4px;
  line-height: 1;
}
.ao-icon-btn:hover { color: var(--ao-accent); }
.ao-icon-btn.danger:hover { color: rgba(255, 100, 100, 0.9); }

.ao-run-meta {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 8px;
  padding: 8px 0;
  border-top: 1px dashed var(--ao-border);
  border-bottom: 1px dashed var(--ao-border);
  margin-bottom: 6px;
}
.ao-meta-item { display: flex; flex-direction: column; gap: 2px; }
.ao-meta-label { font-size: 10px; color: var(--ao-fg-dim); }
.ao-meta-value { font-size: 14px; font-weight: 700; color: rgba(240, 245, 255, 0.95); font-variant-numeric: tabular-nums; }

.ao-run-footer {
  display: flex;
  justify-content: space-between;
  font-size: 10px;
}
.ao-created { color: var(--ao-fg-dim); font-variant-numeric: tabular-nums; }
.ao-view-link { color: var(--ao-accent); }

.ao-detail-header {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 4px 10px;
  border-bottom: 1px dashed var(--ao-border);
  margin-bottom: 12px;
  flex-wrap: wrap;
}

.ao-summary-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 8px;
  margin-bottom: 14px;
}
.ao-summary-card {
  background: var(--ao-bg);
  border: 1px solid var(--ao-border);
  border-radius: 8px;
  padding: 10px 12px;
}
.ao-summary-label { font-size: 10px; color: var(--ao-fg-dim); margin-bottom: 4px; }
.ao-summary-value { font-size: 18px; font-weight: 700; color: rgba(240, 245, 255, 0.95); font-variant-numeric: tabular-nums; }

.ao-charts-grid {
  display: grid;
  grid-template-columns: 1fr;
  gap: 10px;
}
.ao-chart-card {
  background: rgba(20, 26, 48, 0.5);
  border: 1px solid rgba(100, 180, 255, 0.12);
  border-radius: 8px;
  padding: 10px 12px;
}
.ao-chart-head {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  margin-bottom: 6px;
}
.ao-chart-title { font-size: 12px; font-weight: 600; color: rgba(220, 230, 245, 0.9); }
.ao-chart-unit { font-size: 10px; color: var(--ao-fg-dim); }
</style>
