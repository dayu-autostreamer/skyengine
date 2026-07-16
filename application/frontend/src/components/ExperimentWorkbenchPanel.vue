<template>
  <div class="experiment-panel">
    <div class="experiment-tabs">
      <button
        v-for="tab in tabs"
        :key="tab.key"
        class="experiment-tab"
        :class="{ active: activeTab === tab.key }"
        @click="activeTab = tab.key"
      >
        <span>{{ tab.icon }}</span>
        <span>{{ tab.label }}</span>
      </button>
    </div>

    <section v-if="activeTab === 'exception'" class="experiment-section">
      <div class="section-head">
        <h3>Exception 注入</h3>
        <span class="muted">运行中手动扰动真实仿真状态</span>
      </div>

      <div class="form-grid">
        <label>
          类型
          <select v-model="exceptionForm.type">
            <option value="machine_breakdown">机器故障</option>
            <option value="agv_breakdown">AGV 故障</option>
            <option value="temporary_obstacle">临时障碍</option>
          </select>
        </label>

        <label>
          当前 step 后几步触发
          <input v-model.number="exceptionForm.delay_steps" type="number" min="0" />
        </label>

        <label>
          持续步数
          <input v-model.number="exceptionForm.duration_steps" type="number" min="1" />
        </label>

        <label v-if="exceptionForm.type === 'machine_breakdown'">
          机器 ID
          <input v-model.number="exceptionForm.machine_id" type="number" min="0" />
        </label>

        <label v-if="exceptionForm.type === 'agv_breakdown'">
          AGV ID
          <input v-model.number="exceptionForm.agv_id" type="number" min="0" />
        </label>

        <template v-if="exceptionForm.type === 'temporary_obstacle'">
          <label>
            障碍 X
            <input v-model.number="exceptionForm.cell_x" type="number" min="0" />
          </label>
          <label>
            障碍 Y
            <input v-model.number="exceptionForm.cell_y" type="number" min="0" />
          </label>
        </template>

        <label class="span-2">
          原因
          <input v-model.trim="exceptionForm.reason" type="text" placeholder="manual_exception" />
        </label>
      </div>

      <div class="action-row">
        <button class="primary" :disabled="!isRunning || injecting" @click="injectException">
          {{ injecting ? '注入中...' : '注入 Exception' }}
        </button>
        <button class="ghost danger" :disabled="clearing" @click="clearExceptions">
          {{ clearing ? '清理中...' : '清理活跃异常' }}
        </button>
      </div>

      <div class="status-note" :class="{ warn: !isRunning }">
        {{ isRunning ? exceptionStatus : '仿真运行后可立即注入；未来 step 的请求会排入引擎调度。' }}
      </div>
    </section>

    <section v-else-if="activeTab === 'plans'" class="experiment-section">
      <div class="section-head">
        <h3>实验方案</h3>
        <span class="muted">保存算法、配置、exception_config 和 processing_time_config</span>
      </div>

      <div class="plan-save-row">
        <input v-model.trim="planName" type="text" placeholder="方案名称" />
        <button class="primary" :disabled="!currentConfig" @click="savePlan">保存当前方案</button>
        <button class="ghost" @click="pickPlanFile">导入</button>
        <input ref="planFileRef" type="file" accept=".json,application/json" hidden @change="importPlan" />
      </div>

      <div v-if="plans.length === 0" class="empty">暂无实验方案</div>
      <div v-else class="plan-list">
        <div v-for="plan in plans" :key="plan.id" class="plan-card">
          <div>
            <div class="plan-title">{{ plan.name }}</div>
            <div class="plan-meta">
              {{ plan.simulation?.fjsp }} / {{ plan.simulation?.mapf }} / {{ plan.simulation?.assigner }}
              <span>· {{ exceptionLabel(plan.exception_config) }}</span>
            </div>
          </div>
          <div class="card-actions">
            <button class="ghost" @click="loadPlan(plan)">加载</button>
            <button class="ghost" @click="duplicatePlan(plan)">复制</button>
            <button class="ghost" @click="exportPlan(plan)">导出</button>
            <button class="ghost danger" @click="deletePlan(plan.id)">删除</button>
          </div>
        </div>
      </div>
    </section>

    <section v-else-if="activeTab === 'replay'" class="experiment-section">
      <div class="section-head">
        <h3>仿真回放</h3>
        <span class="muted">3D、日志、指标共用同一组历史三流</span>
      </div>

      <div class="archive-row">
        <select v-model="selectedRunId">
          <option value="">当前会话</option>
          <option v-for="run in analysisLog.runs" :key="run.id" :value="run.id">
            {{ run.id }} · {{ run.summary?.total_steps ?? 0 }} steps · {{ run.summary?.insertion_count ?? 0 }} 插单
          </option>
        </select>
        <button class="ghost" @click="analysisLog.listRuns()">刷新</button>
        <button class="ghost" :disabled="!selectedRunId || loadingRun" @click="loadSelectedRun">
          {{ loadingRun ? '加载中...' : '加载归档' }}
        </button>
      </div>

      <div class="replay-controls">
        <button class="primary" :disabled="totalSteps === 0" @click="toggleReplay">
          {{ replayPlaying ? '暂停' : '播放' }}
        </button>
        <select v-model.number="replayInterval">
          <option :value="1200">0.5x</option>
          <option :value="700">1x</option>
          <option :value="350">2x</option>
          <option :value="150">4x</option>
        </select>
        <button class="ghost" :disabled="totalSteps === 0" @click="jumpToLiveTail">跳到末尾</button>
      </div>

      <input
        class="step-range"
        type="range"
        min="0"
        :max="Math.max(0, totalSteps - 1)"
        :value="factoryStore.currentIndex"
        :disabled="totalSteps === 0"
        @input="factoryStore.setIndex($event.target.value)"
      />
      <div class="step-row">
        <span>step {{ currentStep }}</span>
        <span>{{ factoryStore.currentIndex + 1 }}/{{ totalSteps }}</span>
      </div>

      <div class="exception-jumps">
        <div class="mini-title">异常跳转</div>
        <button
          v-for="event in exceptionEvents"
          :key="event.id"
          class="jump-chip"
          @click="jumpToStep(event.step ?? event.idx ?? 0)"
        >
          #{{ event.step ?? event.idx ?? 0 }} {{ event.title || event.type }}
        </button>
        <span v-if="exceptionEvents.length === 0" class="muted">暂无异常事件</span>
      </div>

      <div class="exception-jumps">
        <div class="mini-title">插单跳转</div>
        <button
          v-for="event in insertionEvents"
          :key="event.id"
          class="jump-chip"
          @click="jumpToStep(event.step ?? event.idx ?? 0)"
        >
          #{{ event.step ?? event.idx ?? 0 }} {{ insertionEventLabel(event) }}
        </button>
        <span v-if="insertionEvents.length === 0" class="muted">暂无插单记录</span>
      </div>
    </section>

    <section v-else-if="activeTab === 'compare'" class="experiment-section">
      <div class="section-head">
        <h3>实验对比</h3>
        <span class="muted">选择 2-5 次历史运行</span>
      </div>

      <div class="filter-row">
        <input v-model.trim="runFilter" type="text" placeholder="按算法、异常或 run id 过滤" />
        <button class="ghost" @click="analysisLog.listRuns()">刷新</button>
        <button class="primary" :disabled="selectedCompareIds.length < 2 || comparing" @click="buildComparison">
          {{ comparing ? '计算中...' : '生成对比' }}
        </button>
      </div>

      <div class="compare-pick-list">
        <label v-for="run in filteredRuns" :key="run.id" class="compare-pick">
          <input
            type="checkbox"
            :checked="selectedCompareIds.includes(run.id)"
            :disabled="!selectedCompareIds.includes(run.id) && selectedCompareIds.length >= 5"
            @change="toggleCompareRun(run.id)"
          />
          <span>{{ run.id }}</span>
          <small>{{ run.algorithm || 'no-algorithm' }} · {{ run.summary?.event_total ?? 0 }} events · {{ run.summary?.insertion_count ?? 0 }} 插单</small>
        </label>
      </div>

      <div v-if="compareRows.length" class="compare-table-wrap">
        <table class="compare-table">
          <thead>
            <tr>
              <th>Run</th>
              <th>Makespan</th>
              <th>完成率</th>
              <th>利用率</th>
              <th>异常</th>
              <th>机器故障</th>
              <th>AGV 故障</th>
              <th>Down steps</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="row in compareRows" :key="row.id">
              <td :title="row.id">{{ shortId(row.id) }}</td>
              <td>{{ row.makespan }}</td>
              <td>{{ row.completionRate }}</td>
              <td>{{ row.utilization }}</td>
              <td>{{ row.exceptionTotal }}</td>
              <td>{{ row.machineFailures }}</td>
              <td>{{ row.agvFailures }}</td>
              <td>{{ row.downSteps }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>

    <section v-else class="experiment-section">
      <div class="section-head">
        <h3>异常统计</h3>
      </div>

      <div class="diagnosis-grid">
        <div class="diag-card">
          <span>异常总数</span>
          <strong>{{ diagnosis.total }}</strong>
        </div>
        <div class="diag-card">
          <span>机器故障</span>
          <strong>{{ diagnosis.machine }}</strong>
        </div>
        <div class="diag-card">
          <span>AGV 故障</span>
          <strong>{{ diagnosis.agv }}</strong>
        </div>
        <div class="diag-card">
          <span>临时障碍</span>
          <strong>{{ diagnosis.obstacle }}</strong>
        </div>
      </div>

      <div class="diagnosis-block">
        <div class="mini-title">持续与恢复</div>
        <div v-if="diagnosis.lines.length === 0" class="empty">暂无可诊断异常</div>
        <div v-for="line in diagnosis.lines" :key="line" class="diag-line">{{ line }}</div>
      </div>

      <div class="diagnosis-block">
        <div class="mini-title">影响线索</div>
        <div class="diag-line">AGV 等待累计变化：{{ diagnosis.waitingDelta }}</div>
        <div class="diag-line">机器 down steps：{{ diagnosis.machineDownSteps }}</div>
        <div class="diag-line">AGV down steps：{{ diagnosis.agvDownSteps }}</div>
      </div>
    </section>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { apiPost, API_ROUTES } from '@/utils/api'
import { useFactoryStore } from '@/stores/factory'
import { useMonitorStore } from '@/stores/monitor'
import { useAnalysisLogStore } from '@/stores/analysisLog'

const props = defineProps({
  isRunning: { type: Boolean, default: false },
  simulationMeta: { type: Object, default: () => ({}) },
  exceptionConfig: { type: Object, default: () => ({ preset: 'no_event' }) },
  processingTimeConfig: { type: Object, default: () => ({ preset: 'none' }) },
})

const emit = defineEmits(['load-plan'])

const factoryStore = useFactoryStore()
const monitorStore = useMonitorStore()
const analysisLog = useAnalysisLogStore()

const PLAN_KEY = 'skyengine_grid_factory_experiment_plans'
const exceptionJumpTypes = new Set([
  'machine_breakdown',
  'agv_breakdown',
  'temporary_obstacle',
])
const insertionJumpTypes = new Set([
  'job_insertion_phase_changed',
  'urgent_job_arrival',
  'job_replan_failed',
])

const tabs = [
  { key: 'exception', label: '异常控制', icon: '⚠' },
  { key: 'plans', label: '实验方案', icon: '🧪' },
  { key: 'replay', label: '回放', icon: '▶' },
  { key: 'compare', label: '对比', icon: '▦' },
  { key: 'diagnosis', label: '诊断', icon: '⌁' },
]

const activeTab = ref('exception')
const injecting = ref(false)
const clearing = ref(false)
const exceptionStatus = ref('准备就绪')
const exceptionForm = ref({
  type: 'machine_breakdown',
  delay_steps: 1,
  duration_steps: 12,
  machine_id: 0,
  agv_id: 0,
  cell_x: 1,
  cell_y: 1,
  reason: 'manual_exception',
})

const currentConfig = computed(() => factoryStore.currentConfig)
const currentStep = computed(() => factoryStore.currentState?.timestamp || `#${factoryStore.currentIndex}`)
const totalSteps = computed(() => factoryStore.totalSteps)
const plans = ref(loadPlans())
const planName = ref('')
const planFileRef = ref(null)

const selectedRunId = ref('')
const loadingRun = ref(false)
const replayPlaying = ref(false)
const replayInterval = ref(700)
let replayTimer = null

const runFilter = ref('')
const selectedCompareIds = ref([])
const compareRows = ref([])
const comparing = ref(false)

onMounted(() => {
  analysisLog.listRuns().catch((e) => console.warn('[ExperimentWorkbench] listRuns failed:', e))
})

onBeforeUnmount(() => stopReplay())

watch(replayInterval, () => {
  if (replayPlaying.value) {
    stopReplay()
    startReplay()
  }
})

function buildExceptionBody() {
  const form = exceptionForm.value
  const body = {
    type: form.type,
    delay_steps: Math.max(0, Number(form.delay_steps) || 0),
    reason: form.reason || 'manual_exception',
  }
  if (form.type === 'machine_breakdown') {
    body.machine_id = Number(form.machine_id) || 0
    body.duration_steps = Math.max(1, Number(form.duration_steps) || 1)
  } else if (form.type === 'agv_breakdown') {
    body.agv_id = Number(form.agv_id) || 0
    body.duration_steps = Math.max(1, Number(form.duration_steps) || 1)
  } else if (form.type === 'temporary_obstacle') {
    body.cell = [Number(form.cell_x) || 0, Number(form.cell_y) || 0]
    body.duration_steps = Math.max(1, Number(form.duration_steps) || 1)
  }
  return body
}

async function injectException() {
  injecting.value = true
  try {
    const resp = await apiPost(API_ROUTES.FACTORY_EXCEPTION_INJECT, buildExceptionBody(), { timeout: 30000 })
    if (resp.status === 'error') throw new Error(resp.message || 'Exception 注入失败')
    exceptionStatus.value = resp.status === 'scheduled'
      ? `已排入 step ${resp.step}: ${resp.type}`
      : `已注入: ${resp.type}`
    ElMessage.success(exceptionStatus.value)
  } catch (e) {
    ElMessage.error(e.message || String(e))
  } finally {
    injecting.value = false
  }
}

async function clearExceptions() {
  clearing.value = true
  try {
    const resp = await apiPost(API_ROUTES.FACTORY_EXCEPTION_CLEAR, {}, { timeout: 30000 })
    if (resp.status === 'error') throw new Error(resp.message || 'Exception 清理失败')
    exceptionStatus.value = `已清理 ${resp.cleared?.length || 0} 个活跃异常`
    ElMessage.success(exceptionStatus.value)
  } catch (e) {
    ElMessage.error(e.message || String(e))
  } finally {
    clearing.value = false
  }
}

function loadPlans() {
  try {
    const parsed = JSON.parse(localStorage.getItem(PLAN_KEY) || '[]')
    return Array.isArray(parsed) ? parsed : []
  } catch {
    return []
  }
}

function persistPlans() {
  localStorage.setItem(PLAN_KEY, JSON.stringify(plans.value))
}

function savePlan() {
  if (!currentConfig.value) return
  const planConfig = JSON.parse(JSON.stringify(currentConfig.value))
  planConfig.exception_config = JSON.parse(JSON.stringify(props.exceptionConfig || { preset: 'no_event' }))
  planConfig.processing_time_config = JSON.parse(JSON.stringify(props.processingTimeConfig || { preset: 'none' }))
  planConfig.simulation_control = {
    ...(planConfig.simulation_control || {}),
    max_steps: props.simulationMeta?.max_steps ?? 1000,
  }
  const plan = {
    id: `plan_${Date.now()}`,
    name: planName.value || `实验方案 ${plans.value.length + 1}`,
    created_at: new Date().toISOString(),
    simulation: { ...props.simulationMeta },
    exception_config: JSON.parse(JSON.stringify(props.exceptionConfig || { preset: 'no_event' })),
    processing_time_config: JSON.parse(JSON.stringify(props.processingTimeConfig || { preset: 'none' })),
    config: planConfig,
  }
  plans.value.unshift(plan)
  persistPlans()
  planName.value = ''
  ElMessage.success('实验方案已保存')
}

function loadPlan(plan) {
  emit('load-plan', JSON.parse(JSON.stringify(plan)))
  ElMessage.success('实验方案已加载')
}

function duplicatePlan(plan) {
  plans.value.unshift({
    ...JSON.parse(JSON.stringify(plan)),
    id: `plan_${Date.now()}`,
    name: `${plan.name} 副本`,
    created_at: new Date().toISOString(),
  })
  persistPlans()
}

function deletePlan(id) {
  plans.value = plans.value.filter((p) => p.id !== id)
  persistPlans()
}

function exportPlan(plan) {
  downloadJson(plan, `${plan.name || plan.id}.json`)
}

function pickPlanFile() {
  planFileRef.value?.click()
}

async function importPlan(event) {
  const file = event.target.files?.[0]
  event.target.value = ''
  if (!file) return
  try {
    const plan = JSON.parse(await file.text())
    if (!plan || typeof plan !== 'object' || !plan.config) {
      throw new Error('实验方案必须包含 config')
    }
    plans.value.unshift({
      ...plan,
      id: plan.id || `plan_${Date.now()}`,
      name: plan.name || file.name.replace(/\.json$/i, ''),
      created_at: plan.created_at || new Date().toISOString(),
    })
    persistPlans()
    ElMessage.success('实验方案已导入')
  } catch (e) {
    ElMessage.error(`导入失败: ${e.message}`)
  }
}

function exceptionLabel(config) {
  return config?.preset || (config ? 'custom' : 'no_event')
}

function downloadJson(payload, filename) {
  const blob = new Blob([JSON.stringify(payload, null, 2)], { type: 'application/json' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  setTimeout(() => URL.revokeObjectURL(url), 1000)
}

async function loadSelectedRun() {
  if (!selectedRunId.value) return
  loadingRun.value = true
  try {
    const run = await analysisLog.loadRun(selectedRunId.value)
    if (!run) throw new Error(analysisLog.error || '归档不存在')
    const frames = JSON.parse(JSON.stringify(run.frames || []))
    if (frames.length && Array.isArray(run.insertionRequests)) {
      const hasFrameRecords = frames.some((frame) => Array.isArray(frame.insertion_requests))
      if (!hasFrameRecords) frames[frames.length - 1].insertion_requests = run.insertionRequests
    }
    factoryStore.loadData(frames)
    monitorStore.loadArchiveData(run.metricsTimeline || [], run.events || [])
    stopReplay()
    activeTab.value = 'replay'
    ElMessage.success('归档已加载到回放视图')
  } catch (e) {
    ElMessage.error(e.message || String(e))
  } finally {
    loadingRun.value = false
  }
}

function toggleReplay() {
  replayPlaying.value ? stopReplay() : startReplay()
}

function startReplay() {
  if (totalSteps.value === 0) return
  replayPlaying.value = true
  clearInterval(replayTimer)
  replayTimer = setInterval(() => {
    if (factoryStore.currentIndex >= totalSteps.value - 1) {
      stopReplay()
      return
    }
    factoryStore.setIndex(factoryStore.currentIndex + 1)
  }, replayInterval.value)
}

function stopReplay() {
  replayPlaying.value = false
  if (replayTimer) {
    clearInterval(replayTimer)
    replayTimer = null
  }
}

function jumpToLiveTail() {
  stopReplay()
  factoryStore.setIndex(Math.max(0, totalSteps.value - 1))
}

function jumpToStep(step) {
  const idx = factoryStore.historyBuffer.findIndex((frame, i) => {
    const raw = frame.timestamp || frame.env_timeline || ''
    const parsed = parseInt(String(raw).replace(/[^\d]/g, ''), 10)
    return Number.isFinite(parsed) ? parsed >= Number(step) : i >= Number(step)
  })
  factoryStore.setIndex(idx >= 0 ? idx : Number(step) || 0)
}

const exceptionEvents = computed(() =>
  (monitorStore.events || []).filter((event) => exceptionJumpTypes.has(event.type))
)

const insertionEvents = computed(() =>
  (monitorStore.events || []).filter((event) => insertionJumpTypes.has(event.type))
)

function insertionEventLabel(event) {
  const phase = event.payload?.phase
  const phaseLabels = {
    queued: '排队', replanning: '重规划', scheduled: '已排程',
    transporting: '运输中', processing: '加工中', completed: '已完成', failed: '失败',
  }
  const requestId = event.payload?.request_id || '插单'
  return `${requestId} ${phaseLabels[phase] || event.title || event.type}`
}

const filteredRuns = computed(() => {
  const q = runFilter.value.toLowerCase()
  const runs = analysisLog.runs || []
  if (!q) return runs
  return runs.filter((run) => {
    const haystack = [
      run.id,
      run.algorithm,
      run.factory_id,
      JSON.stringify(run.summary?.event_counts || {}),
    ].join(' ').toLowerCase()
    return haystack.includes(q)
  })
})

function toggleCompareRun(id) {
  if (selectedCompareIds.value.includes(id)) {
    selectedCompareIds.value = selectedCompareIds.value.filter((item) => item !== id)
  } else if (selectedCompareIds.value.length < 5) {
    selectedCompareIds.value.push(id)
  }
}

async function buildComparison() {
  comparing.value = true
  try {
    const rows = []
    for (const id of selectedCompareIds.value) {
      const detail = await analysisLog.loadRun(id)
      if (!detail) continue
      rows.push(makeCompareRow(detail))
    }
    compareRows.value = rows
  } finally {
    comparing.value = false
  }
}

function makeCompareRow(run) {
  const summary = run.summary || {}
  const counts = summary.event_counts || {}
  const latestMetrics = [...(run.metricsTimeline || [])].reverse().find((item) => item?.metrics)?.metrics || {}
  const totalJobs = summary.total_jobs || 0
  const completedJobs = summary.completed_jobs || 0
  const utilization = summary.avg_utilization == null ? '--' : `${(summary.avg_utilization * 100).toFixed(1)}%`
  return {
    id: run.id,
    makespan: summary.total_steps ?? run.total_steps ?? '--',
    completionRate: totalJobs ? `${((completedJobs / totalJobs) * 100).toFixed(0)}%` : '--',
    utilization,
    exceptionTotal: counts.machine_breakdown || counts.agv_breakdown || counts.temporary_obstacle
      ? (counts.machine_breakdown || 0) + (counts.agv_breakdown || 0) + (counts.temporary_obstacle || 0)
      : (latestMetrics.machine_failure_count || 0)
        + (latestMetrics.agv_failure_count || 0)
        + (latestMetrics.temporary_obstacle_count || 0),
    machineFailures: counts.machine_breakdown || latestMetrics.machine_failure_count || 0,
    agvFailures: counts.agv_breakdown || latestMetrics.agv_failure_count || 0,
    downSteps: (latestMetrics.machine_down_steps_total || 0) + (latestMetrics.agv_down_steps_total || 0),
  }
}

function shortId(id) {
  return String(id || '').slice(0, 14)
}

function eventStep(event) {
  const step = Number(event?.step ?? event?.idx ?? 0)
  return Number.isFinite(step) ? step : 0
}

function enqueueOpen(openMap, key, record) {
  if (!openMap.has(key)) openMap.set(key, [])
  openMap.get(key).push(record)
}

function closeOpen(openMap, key, recoveryStep) {
  const queue = openMap.get(key)
  if (!queue || queue.length === 0) return
  const record = queue.shift()
  record.recoveryStep = recoveryStep
}

function pairExceptionDurations(events) {
  const records = []
  const openMachines = new Map()
  const openAgvs = new Map()
  const openObstacles = new Map()
  const sorted = [...events].sort((a, b) => eventStep(a) - eventStep(b))

  sorted.forEach((event) => {
    const step = eventStep(event)
    if (event.type === 'machine_breakdown') {
      const machineId = event.payload?.machine_id
      const record = {
        type: 'machine',
        label: event.payload?.display_name || factoryStore.getMachineDisplayName(machineId),
        startStep: step,
        recoveryStep: null,
      }
      records.push(record)
      enqueueOpen(openMachines, String(machineId), record)
    } else if (event.type === 'machine_recovery') {
      closeOpen(openMachines, String(event.payload?.machine_id), step)
    } else if (event.type === 'agv_breakdown') {
      const agvId = event.payload?.agv_id
      const record = { type: 'agv', label: `AGV-${agvId}`, startStep: step, recoveryStep: null }
      records.push(record)
      enqueueOpen(openAgvs, String(agvId), record)
    } else if (event.type === 'agv_recovery') {
      closeOpen(openAgvs, String(event.payload?.agv_id), step)
    } else if (event.type === 'temporary_obstacle') {
      const cellKey = JSON.stringify(event.payload?.cell ?? null)
      const record = { type: 'obstacle', label: `临时障碍 ${cellKey}`, startStep: step, recoveryStep: null }
      records.push(record)
      enqueueOpen(openObstacles, cellKey, record)
    } else if (event.type === 'obstacle_clear') {
      closeOpen(openObstacles, JSON.stringify(event.payload?.cell ?? null), step)
    }
  })

  return records.map((record) => {
    if (record.type === 'obstacle') {
      return `${record.label} step ${record.startStep}，清除 step ${record.recoveryStep ?? '未清除'}`
    }
    return `${record.label} 故障 step ${record.startStep}，恢复 step ${record.recoveryStep ?? '未恢复'}`
  })
}

const diagnosis = computed(() => {
  const events = monitorStore.events || []
  const metrics = monitorStore.metricsTimeline || []
  const machine = events.filter((event) => event.type === 'machine_breakdown').length
  const agv = events.filter((event) => event.type === 'agv_breakdown').length
  const obstacle = events.filter((event) => event.type === 'temporary_obstacle').length
  const counts = {
    total: machine + agv + obstacle,
    machine,
    agv,
    obstacle,
  }
  const lines = pairExceptionDurations(events)
  const first = metrics[0]?.metrics || {}
  const last = metrics[metrics.length - 1]?.metrics || {}
  const waitingDelta = Number(last.agv_waiting_time_total || 0) - Number(first.agv_waiting_time_total || 0)
  return {
    ...counts,
    lines,
    waitingDelta: Number.isFinite(waitingDelta) ? waitingDelta.toFixed(1) : '--',
    machineDownSteps: last.machine_down_steps_total ?? 0,
    agvDownSteps: last.agv_down_steps_total ?? 0,
  }
})
</script>

<style scoped>
.experiment-panel {
  height: 100%;
  display: flex;
  flex-direction: column;
  color: rgba(220, 230, 245, 0.92);
}
.experiment-tabs {
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  border-bottom: 1px solid rgba(100, 180, 255, 0.12);
}
.experiment-tab {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2px;
  padding: 7px 2px;
  border: 0;
  background: transparent;
  color: rgba(160, 190, 230, 0.62);
  font-size: 10px;
  cursor: pointer;
}
.experiment-tab.active {
  color: #8fd0ff;
  background: rgba(100, 180, 255, 0.08);
}
.experiment-section {
  flex: 1;
  overflow-y: auto;
  padding: 10px;
}
.section-head {
  display: flex;
  flex-direction: column;
  gap: 2px;
  margin-bottom: 10px;
}
.section-head h3 {
  margin: 0;
  font-size: 13px;
}
.muted {
  color: rgba(160, 190, 230, 0.48);
  font-size: 10px;
}
.form-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 8px;
}
label {
  display: flex;
  flex-direction: column;
  gap: 4px;
  color: rgba(160, 190, 230, 0.7);
  font-size: 10px;
}
.span-2 {
  grid-column: span 2;
}
input,
select {
  width: 100%;
  box-sizing: border-box;
  padding: 7px 8px;
  border-radius: 6px;
  border: 1px solid rgba(100, 180, 255, 0.16);
  background: rgba(20, 25, 45, 0.65);
  color: rgba(220, 230, 245, 0.94);
  font-size: 12px;
  outline: none;
}
select option {
  background: #141929;
}
.action-row,
.plan-save-row,
.archive-row,
.replay-controls,
.filter-row,
.card-actions {
  display: flex;
  gap: 8px;
  align-items: center;
}
.action-row,
.plan-save-row,
.archive-row,
.replay-controls,
.filter-row {
  margin: 10px 0;
}
button {
  border: 1px solid rgba(100, 180, 255, 0.18);
  border-radius: 6px;
  background: rgba(60, 120, 200, 0.18);
  color: rgba(220, 230, 245, 0.9);
  padding: 7px 9px;
  font-size: 11px;
  cursor: pointer;
  white-space: nowrap;
}
button.primary {
  background: rgba(80, 130, 230, 0.46);
  border-color: rgba(120, 180, 255, 0.42);
}
button.ghost {
  background: rgba(255, 255, 255, 0.04);
}
button.danger {
  border-color: rgba(255, 100, 100, 0.28);
  color: #ff9a9a;
}
button:disabled {
  opacity: 0.42;
  cursor: not-allowed;
}
.status-note {
  padding: 8px;
  border-radius: 6px;
  background: rgba(100, 180, 255, 0.07);
  color: rgba(190, 220, 255, 0.78);
  font-size: 11px;
}
.status-note.warn {
  background: rgba(255, 180, 80, 0.08);
  color: rgba(255, 210, 150, 0.78);
}
.empty {
  padding: 18px 0;
  text-align: center;
  color: rgba(160, 190, 230, 0.45);
  font-size: 12px;
}
.plan-list,
.compare-pick-list,
.exception-jumps,
.diagnosis-block {
  display: flex;
  flex-direction: column;
  gap: 7px;
}
.plan-card {
  display: flex;
  justify-content: space-between;
  gap: 8px;
  padding: 8px;
  border: 1px solid rgba(100, 180, 255, 0.12);
  border-radius: 7px;
  background: rgba(20, 26, 48, 0.52);
}
.plan-title {
  font-weight: 600;
  font-size: 12px;
}
.plan-meta {
  margin-top: 3px;
  color: rgba(160, 190, 230, 0.52);
  font-size: 10px;
}
.card-actions {
  flex-wrap: wrap;
  justify-content: flex-end;
}
.step-range {
  padding: 0;
}
.step-row {
  display: flex;
  justify-content: space-between;
  color: rgba(160, 190, 230, 0.66);
  font-size: 11px;
  font-variant-numeric: tabular-nums;
}
.mini-title {
  margin: 10px 0 4px;
  color: #8fd0ff;
  font-size: 10px;
  font-weight: 700;
}
.jump-chip {
  text-align: left;
  overflow: hidden;
  text-overflow: ellipsis;
}
.compare-pick {
  display: grid;
  grid-template-columns: auto 1fr;
  column-gap: 6px;
  padding: 6px 8px;
  border-radius: 6px;
  background: rgba(255, 255, 255, 0.035);
}
.compare-pick input {
  width: auto;
  grid-row: span 2;
}
.compare-pick small {
  color: rgba(160, 190, 230, 0.5);
}
.compare-table-wrap {
  overflow-x: auto;
}
.compare-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 10px;
  font-variant-numeric: tabular-nums;
}
.compare-table th,
.compare-table td {
  padding: 6px;
  border-bottom: 1px solid rgba(100, 180, 255, 0.1);
  text-align: left;
}
.diagnosis-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 8px;
}
.diag-card {
  padding: 9px;
  border-radius: 7px;
  background: rgba(20, 26, 48, 0.58);
  border: 1px solid rgba(100, 180, 255, 0.12);
}
.diag-card span {
  display: block;
  color: rgba(160, 190, 230, 0.56);
  font-size: 10px;
}
.diag-card strong {
  display: block;
  margin-top: 4px;
  font-size: 18px;
}
.diag-line {
  padding: 6px 8px;
  border-radius: 6px;
  background: rgba(255, 255, 255, 0.035);
  color: rgba(220, 230, 245, 0.82);
  font-size: 11px;
}
</style>
