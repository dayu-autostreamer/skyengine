<template>
  <Teleport to="body">
  <DraggablePanel
    v-if="visible"
    title="🎯 焦点"
    :width="FP_WIDTH"
    :max-height="520"
    :collapsible="false"
    :initial-pos="initialPos"
    @close="handleClose"
  >
    <!-- Tab 栏（sticky：内容滚动时固定在顶部） -->
    <div class="fp-tabs">
      <button
        v-for="t in tabs"
        :key="t.key"
        class="fp-tab"
        :class="{ active: activeTab === t.key, has_sel: hasSelection(t.key) }"
        @click="activeTab = t.key"
      >
        <span class="fp-tab-icon">{{ t.icon }}</span>
        <span class="fp-tab-label">{{ t.label }}</span>
        <span v-if="hasSelection(t.key)" class="fp-dot"></span>
      </button>
    </div>

    <!-- 内容区 -->
    <div class="fp-content">
      <!-- Machine -->
      <template v-if="activeTab === 'machine'">
        <template v-if="selectedMachine">
          <div class="fp-head">
            <span class="fp-title">⚙️ {{ selectedMachineName }}</span>
            <span class="fp-tag" :class="`tag-${machineStatusClass}`">{{ selectedMachine.status || (selectedMachine.current_op ? 'WORKING' : 'IDLE') }}</span>
          </div>

          <div class="fp-row">
            <span class="fp-k">编号</span>
            <span class="fp-v">{{ selectedMachineKey }}</span>
          </div>
          <div class="fp-row">
            <span class="fp-k">数据时点</span>
            <span class="fp-v">step {{ currentStep }}</span>
          </div>
          <div class="fp-row">
            <span class="fp-k">位置</span>
            <span class="fp-v">{{ fmtLoc(selectedMachine.location || selectedMachineConfig?.location) }}</span>
          </div>
          <div class="fp-row">
            <span class="fp-k">当前队列</span>
            <span class="fp-v">{{ selectedMachine.queue_length ?? 0 }}</span>
          </div>
          <div v-if="selectedMachine.repair_remaining > 0" class="fp-row fp-row-alert">
            <span class="fp-k">维修剩余</span>
            <span class="fp-v">{{ selectedMachine.repair_remaining }} 步</span>
          </div>
          <div v-if="selectedMachine.down_reason" class="fp-row fp-row-alert">
            <span class="fp-k">异常原因</span>
            <span class="fp-v fp-v-wrap">{{ selectedMachine.down_reason }}</span>
          </div>
          <div v-if="machineStatusClass !== 'broken'" class="fp-row">
            <span class="fp-k">故障概率</span>
            <span class="fp-v fp-v-wrap">{{ machineFailureProbability }}</span>
          </div>
          <div v-if="nextMachineException" class="fp-row">
            <span class="fp-k">下次计划故障</span>
            <span class="fp-v fp-v-wrap">{{ nextMachineException }}</span>
          </div>
          <div class="fp-row">
            <span class="fp-k">加工时间波动</span>
            <span class="fp-v fp-v-wrap">{{ processingTimeSummary }}</span>
          </div>

          <div class="fp-section">运行统计</div>
          <div class="fp-stat-grid">
            <div class="fp-stat"><strong>{{ machineRuntime.activityRate }}</strong><span>工作占比</span></div>
            <div class="fp-stat"><strong>{{ machineRuntime.avgQueue }}</strong><span>近期均队列</span></div>
            <div class="fp-stat"><strong>{{ machineRuntime.maxQueue }}</strong><span>最大队列</span></div>
            <div class="fp-stat"><strong>{{ machineRuntime.finishedOps }}</strong><span>完工工序</span></div>
          </div>

          <template v-if="selectedMachine.current_op">
            <div class="fp-section">当前工序</div>
            <div class="fp-row">
              <span class="fp-k">Job-Op</span>
              <span class="fp-v">Job{{ selectedMachine.current_op.job_id }}-Op{{ selectedMachine.current_op.op_id }}</span>
            </div>
            <div v-if="currentOperationTime" class="fp-row">
              <span class="fp-k">加工用时</span>
              <span class="fp-v fp-v-wrap">{{ currentOperationTime }}</span>
            </div>
            <div class="fp-progress">
              <div class="fp-progress-head">
                <span>Op 步数</span>
                <span>{{ selectedMachine.current_op.step_done }}/{{ selectedMachine.current_op.proc_time }}</span>
              </div>
              <div class="fp-bar-wrap">
                <div class="fp-bar bar-op" :style="{ width: opStepPct + '%' }"></div>
              </div>
            </div>
            <div class="fp-progress">
              <div class="fp-progress-head">
                <span>Job 进度</span>
                <span>{{ (selectedMachine.current_op.index_in_job ?? 0) + 1 }}/{{ selectedMachine.current_op.total_in_job }}</span>
              </div>
              <div class="fp-bar-wrap">
                <div class="fp-bar bar-job" :style="{ width: opJobPct + '%' }"></div>
              </div>
            </div>
          </template>
          <div v-else class="fp-empty-inline">空闲</div>
        </template>
        <div v-else class="fp-placeholder">
          <span class="fp-ph-icon">⚙️</span>
          <p>点击机器卡片查看详情</p>
        </div>
      </template>

      <!-- Job -->
      <template v-else-if="activeTab === 'job'">
        <template v-if="selectedJob">
          <div class="fp-head">
            <span class="fp-title">📦 {{ selectedJobName }}</span>
            <span class="fp-tag" :class="selectedJob.is_completed ? 'tag-completed' : 'tag-progress'">
              {{ selectedJob.is_completed ? '已完成' : `${selectedJob.progress.done}/${selectedJob.progress.total}` }}
            </span>
          </div>

          <div class="fp-row">
            <span class="fp-k">编号 / 优先级</span>
            <span class="fp-v">Job{{ selectedJob.job_id }} / {{ selectedJobPriority }}</span>
          </div>
          <div class="fp-row">
            <span class="fp-k">数据时点</span>
            <span class="fp-v">step {{ currentStep }}</span>
          </div>
          <div class="fp-row">
            <span class="fp-k">交期</span>
            <span class="fp-v">{{ selectedJob.due ?? selectedJobConfig?.due_time ?? '—' }}</span>
          </div>
          <div class="fp-row">
            <span class="fp-k">完工</span>
            <span class="fp-v">{{ selectedJob.completion_time ?? '—' }}</span>
          </div>
          <div class="fp-row">
            <span class="fp-k">释放</span>
            <span class="fp-v">{{ selectedJob.release ?? selectedJobConfig?.arrival_time ?? '—' }}</span>
          </div>
          <div class="fp-row">
            <span class="fp-k">已运行 / 延期</span>
            <span class="fp-v" :class="{ 'fp-v-danger': jobRuntime.isLate }">
              {{ jobRuntime.elapsed }} / {{ jobRuntime.lateness }}
            </span>
          </div>

          <div class="fp-progress">
            <div class="fp-progress-head">
              <span>总进度</span>
              <span>{{ selectedJob.progress.done }}/{{ selectedJob.progress.total }}</span>
            </div>
            <div class="fp-bar-wrap">
              <div class="fp-bar bar-job" :style="{ width: jobPct + '%' }"></div>
            </div>
          </div>

          <div class="fp-section">工序列表 ({{ selectedJob.ops.length }})</div>
          <div class="fp-op-summary">
            <span>待处理 {{ jobOpSummary.pending }}</span>
            <span>加工中 {{ jobOpSummary.processing }}</span>
            <span>已完成 {{ jobOpSummary.finished }}</span>
          </div>
          <div class="fp-op-list">
            <div
              v-for="op in selectedJob.ops"
              :key="op.op_id"
              class="fp-op-row"
              :class="`op-${(op.status || '').toLowerCase()}`"
            >
              <span class="fp-op-id">Op{{ op.op_id }}</span>
              <span class="fp-op-status">{{ op.status }}</span>
              <span class="fp-op-mach" :title="op.assigned_machine != null ? `运行 ID: M${op.assigned_machine}` : ''">
                {{ formatAssignedMachine(op.assigned_machine) }}
              </span>
              <span class="fp-op-time">{{ op.proc_time }}t</span>
            </div>
          </div>
        </template>
        <div v-else class="fp-placeholder">
          <span class="fp-ph-icon">📦</span>
          <p>点击 Job 卡片查看详情</p>
        </div>
      </template>

      <!-- AGV -->
      <template v-else-if="activeTab === 'agv'">
        <template v-if="selectedAgvIndex != null && agvCount > 0">
          <div class="fp-head">
            <span class="fp-title">🤖 {{ selectedAgvName }}</span>
            <span class="fp-tag" :class="selectedAgvStatus === 'DOWN' ? 'tag-broken' : (selectedAgvActive ? 'tag-working' : 'tag-idle')">
              {{ selectedAgvStatusLabel }}
            </span>
          </div>
          <div class="fp-row">
            <span class="fp-k">编号</span>
            <span class="fp-v">{{ selectedAgvConfig?.id ?? selectedAgvIndex }}</span>
          </div>
          <div class="fp-row">
            <span class="fp-k">数据时点</span>
            <span class="fp-v">step {{ currentStep }}</span>
          </div>
          <div class="fp-row">
            <span class="fp-k">坐标</span>
            <span class="fp-v">[{{ selectedAgvPos[0] }}, {{ selectedAgvPos[1] }}]</span>
          </div>
          <div class="fp-row">
            <span class="fp-k">目标坐标</span>
            <span class="fp-v">{{ fmtLoc(selectedAgvTarget) }}</span>
          </div>
          <div class="fp-row">
            <span class="fp-k">初始坐标</span>
            <span class="fp-v">{{ fmtLoc(selectedAgvConfig?.initialLocation) }}</span>
          </div>
          <div class="fp-row">
            <span class="fp-k">容量</span>
            <span class="fp-v">{{ selectedAgvConfig?.capacity ?? '—' }}</span>
          </div>
          <div v-if="selectedAgvRepairRemaining > 0" class="fp-row fp-row-alert">
            <span class="fp-k">维修剩余</span>
            <span class="fp-v">{{ selectedAgvRepairRemaining }} 步</span>
          </div>
          <div v-if="selectedAgvStatus !== 'DOWN'" class="fp-row">
            <span class="fp-k">故障概率</span>
            <span class="fp-v fp-v-wrap">{{ agvFailureProbability }}</span>
          </div>
          <div v-if="nextAgvException" class="fp-row">
            <span class="fp-k">下次计划故障</span>
            <span class="fp-v fp-v-wrap">{{ nextAgvException }}</span>
          </div>

          <div class="fp-section">运行统计</div>
          <div class="fp-stat-grid">
            <div class="fp-stat"><strong>{{ selectedAgvRuntime.activityRate }}</strong><span>活动占比</span></div>
            <div class="fp-stat"><strong>{{ selectedAgvRuntime.distance }}</strong><span>移动格数</span></div>
            <div class="fp-stat"><strong>{{ selectedAgvRuntime.activeFrames }}</strong><span>活动帧</span></div>
            <div class="fp-stat"><strong>{{ selectedAgvRuntime.totalFrames }}</strong><span>统计帧</span></div>
          </div>
        </template>
        <div v-else-if="agvCount > 0" class="fp-placeholder">
          <span class="fp-ph-icon">🤖</span>
          <p>点击 AGV 卡片查看详情</p>
        </div>
        <div v-else class="fp-placeholder">
          <span class="fp-ph-icon">🤖</span>
          <p>等待 AGV 数据...</p>
        </div>
      </template>
    </div>
  </DraggablePanel>

  <!-- 收起后的浮标（有内容可看时才显示） -->
  <button v-else-if="showPill" class="focus-panel-collapsed" title="展开焦点面板" @click="reopen">
    🎯
  </button>
  </Teleport>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { useFactoryStore } from '@/stores/factory'
import DraggablePanel from './DraggablePanel.vue'

const store = useFactoryStore()

const EXCEPTION_PRESETS = {
  no_event: {},
  mild_failure: {
    machine_failure: { enabled: true, mtbf_steps: 300, busy_only: true },
    agv_failure: { enabled: true, mtbf_steps: 500, busy_only: false },
  },
  moderate_failure: {
    machine_failure: { enabled: true, mtbf_steps: 180, busy_only: false },
    agv_failure: { enabled: true, mtbf_steps: 260, busy_only: false },
    temporary_obstacle: { enabled: true, mean_interarrival_steps: 140 },
  },
  stress_failure: {
    machine_failure: { enabled: true, mtbf_steps: 30, busy_only: false },
    agv_failure: { enabled: true, mtbf_steps: 50, busy_only: false },
    temporary_obstacle: { enabled: true, mean_interarrival_steps: 35 },
  },
  routing_disruption: {
    temporary_obstacle: { enabled: true, mean_interarrival_steps: 25 },
  },
}

const PROCESSING_TIME_PRESETS = {
  none: { enabled: false },
  no_variance: { enabled: false },
  mild_variance: {
    enabled: true,
    default_distribution: { dist: 'multiplier_uniform', low: 0.9, high: 1.1 },
  },
  moderate_variance: {
    enabled: true,
    default_distribution: { dist: 'multiplier_uniform', low: 0.8, high: 1.25 },
  },
  high_variance: {
    enabled: true,
    default_distribution: { dist: 'multiplier_uniform', low: 0.6, high: 1.6 },
  },
}

const FP_WIDTH = 280
const FP_HEIGHT = 480
// 初始位置：左下角，与 FactoryTabsPanel（x=12, width=300, height=480）左对齐
// FactoryTabsPanel 占 y∈[12, 492]，FocusPanel 接在正下方
const FP_OFFSET_TOP = 12 + 480 + 8  // = 500
const initialPos = {
  x: 12,
  y: Math.max(FP_OFFSET_TOP, (typeof window !== 'undefined' ? window.innerHeight : 800) - FP_HEIGHT - 12),
}

// 收起/展开：closed 与选中态解耦，× 真正能关掉
// pinned 默认 true：页面加载后直接显示占位面板，不依赖选中态
const closed = ref(false)
const pinned = ref(true)

const tabs = [
  { key: 'machine', label: '机器', icon: '⚙️' },
  { key: 'job',     label: 'Job', icon: '📦' },
  { key: 'agv',     label: 'AGV', icon: '🤖' },
]

const activeTab = ref('machine')

const selectedMachineKey = computed(() => store.selectedMachineKey)
const selectedJobId = computed(() => store.selectedJobId)
const selectedAgvIndex = computed(() => store.selectedAgvIndex)
const focusState = computed(() => store.currentState)

function mergeProfile(presets, config) {
  const explicit = config && typeof config === 'object' ? config : {}
  const base = presets[explicit.preset] || {}
  const merged = { ...base, ...explicit }
  for (const key of new Set([...Object.keys(base), ...Object.keys(explicit)])) {
    if (base[key] && typeof base[key] === 'object' && explicit[key] && typeof explicit[key] === 'object') {
      merged[key] = { ...base[key], ...explicit[key] }
    }
  }
  return merged
}

const activeExceptionConfig = computed(() => mergeProfile(
  EXCEPTION_PRESETS,
  store.runtimeExceptionConfig || store.currentConfig?.exception_config,
))
const activeProcessingTimeConfig = computed(() => mergeProfile(
  PROCESSING_TIME_PRESETS,
  store.runtimeProcessingTimeConfig || store.currentConfig?.processing_time_config,
))

function numericId(value) {
  const match = String(value ?? '').match(/\d+/)
  return match ? Number(match[0]) : null
}

function machineFromSnapshot(machines, key) {
  if (!machines || key == null) return null
  const runtimeKey = typeof store.getMachineRuntimeKey === 'function'
    ? store.getMachineRuntimeKey(key, { machines })
    : key
  return machines[runtimeKey] || null
}

const selectedMachineConfig = computed(() => {
  if (typeof store.getMachineConfig === 'function') {
    return store.getMachineConfig(selectedMachineKey.value, focusState.value)
  }
  const runtimeId = String(selectedMachineKey.value ?? '').match(/^M(\d+)$/i)?.[1]
  const configKey = store.getJobMachineIdMap?.()[runtimeId]
  return store.getCurrentAssets?.().machines?.[configKey] || null
})

const selectedMachine = computed(() => {
  const key = selectedMachineKey.value
  if (!key) return null

  const snapshotMachines = focusState.value?.machines || {}
  return machineFromSnapshot(snapshotMachines, key) || selectedMachineConfig.value
})

const selectedMachineName = computed(() =>
  store.getMachineDisplayName(selectedMachineKey.value, focusState.value),
)

const selectedJobConfig = computed(() => {
  if (selectedJobId.value == null) return null
  return (store.getJobs?.() || []).find((job) => String(job.job_id) === String(selectedJobId.value)) || null
})

const selectedJob = computed(() => {
  if (selectedJobId.value == null) return null
  const live = focusState.value?.jobs?.find((job) => String(job.job_id) === String(selectedJobId.value))
  if (live) return live
  const config = selectedJobConfig.value
  if (!config) return null
  const ops = (config.operations || []).map((op, index) => ({
    op_id: index,
    status: 'PENDING',
    proc_time: op.duration ?? 0,
    assigned_machine: op.machine_id ?? null,
  }))
  return {
    job_id: config.job_id,
    release: config.arrival_time ?? 0,
    due: config.due_time ?? null,
    completion_time: null,
    is_completed: false,
    progress: { done: 0, total: ops.length },
    ops,
  }
})

const machineRuntime = computed(() => {
  const frames = (store.historyBuffer || []).slice(-120)
  const machines = frames
    .map((frame) => machineFromSnapshot(frame.machines || {}, selectedMachineKey.value))
    .filter(Boolean)
  const working = machines.filter((machine) =>
    String(machine.status || '').toUpperCase() === 'WORKING' || machine.current_op,
  ).length
  const queues = machines.map((machine) => machine.queue_length).filter(Number.isFinite)
  const selectedId = numericId(selectedMachine.value?.id ?? selectedMachineKey.value)
  const finishedOps = (focusState.value?.jobs || []).reduce((count, job) => (
    count + (job.ops || []).filter((op) =>
      op.status === 'FINISHED' && numericId(op.assigned_machine) === selectedId,
    ).length
  ), 0)
  return {
    activityRate: machines.length > 0 ? `${Math.round((working / machines.length) * 100)}%` : '—',
    avgQueue: queues.length > 0
      ? (queues.reduce((sum, value) => sum + value, 0) / queues.length).toFixed(1)
      : '—',
    maxQueue: queues.length > 0 ? Math.max(...queues) : '—',
    finishedOps,
  }
})

const machineStatusClass = computed(() => {
  const m = selectedMachine.value
  if (!m) return 'idle'
  const status = m.status || (m.current_op ? 'WORKING' : 'IDLE')
  return status.toLowerCase()
})

const opStepPct = computed(() => {
  const op = selectedMachine.value?.current_op
  return op && op.proc_time > 0 ? Math.min(100, Math.round((op.step_done / op.proc_time) * 100)) : 0
})
const opJobPct = computed(() => {
  const op = selectedMachine.value?.current_op
  return op && op.total_in_job > 0 ? Math.min(100, Math.round(((op.index_in_job + 1) / op.total_in_job) * 100)) : 0
})

function formatDistribution(distribution) {
  if (!distribution || typeof distribution !== 'object') return '无波动'
  const dist = distribution.dist || distribution.type
  if (dist === 'multiplier_uniform') return `${distribution.low}~${distribution.high} × 基准加工时间`
  if (dist === 'uniform' || dist === 'discrete_uniform') return `${distribution.low}~${distribution.high} 步均匀分布`
  if (dist === 'fixed') return `固定 ${distribution.value} 步`
  if (dist === 'normal') return `正态分布 μ=${distribution.mean}, σ=${distribution.std}`
  return dist || '自定义分布'
}

const processingTimeSummary = computed(() => {
  const opDistribution = selectedMachine.value?.current_op?.processing_time_distribution
  if (opDistribution) return formatDistribution(opDistribution)
  const config = activeProcessingTimeConfig.value
  if (config.enabled === false || config.preset === 'none' || config.preset === 'no_variance') return '无波动'
  return formatDistribution(config.default_distribution || config.distribution || config.processing_time_distribution)
})

const currentOperationTime = computed(() => {
  const op = selectedMachine.value?.current_op
  if (!op) return null
  const nominal = op.nominal_proc_time ?? op.proc_time
  const sampled = op.sampled_proc_time ?? op.proc_time
  return `基准 ${nominal} 步，本次实际 ${sampled} 步`
})

function formatAssignedMachine(machineId) {
  return store.getMachineDisplayName(machineId, focusState.value)
}
const jobPct = computed(() => {
  const j = selectedJob.value
  return j && j.progress.total > 0 ? Math.round((j.progress.done / j.progress.total) * 100) : 0
})

const currentStep = computed(() => numericId(focusState.value?.env_timeline) ?? 0)
const selectedJobName = computed(() =>
  selectedJobConfig.value?.name || selectedJob.value?.name || `Job${selectedJob.value?.job_id ?? ''}`,
)
const selectedJobPriority = computed(() =>
  selectedJob.value?.priority ?? selectedJobConfig.value?.priority ?? '普通',
)
const jobRuntime = computed(() => {
  const job = selectedJob.value
  if (!job) return { elapsed: '—', lateness: '—', isLate: false }
  const release = Number(job.release ?? selectedJobConfig.value?.arrival_time ?? 0)
  const due = Number(job.due ?? selectedJobConfig.value?.due_time)
  const end = Number(job.completion_time ?? currentStep.value)
  const elapsed = Math.max(0, end - release)
  const lateness = Number.isFinite(due) ? Math.max(0, end - due) : null
  return {
    elapsed: `${elapsed} 步`,
    lateness: lateness == null ? '无交期' : (lateness > 0 ? `${lateness} 步` : '未延期'),
    isLate: lateness > 0,
  }
})
const jobOpSummary = computed(() => {
  const summary = { pending: 0, processing: 0, finished: 0 }
  ;(selectedJob.value?.ops || []).forEach((op) => {
    const status = String(op.status || 'PENDING').toLowerCase()
    if (status in summary) summary[status] += 1
    else summary.pending += 1
  })
  return summary
})

// AGV 派生
const positions = computed(() => focusState.value?.grid_state?.positions_xy || [])
const isActiveArr = computed(() => focusState.value?.grid_state?.is_active || [])
const agvStatusArr = computed(() => focusState.value?.grid_state?.agv_status || [])
const agvRepairArr = computed(() => focusState.value?.grid_state?.agv_repair_remaining || [])
const agvTargets = computed(() =>
  focusState.value?.grid_state?.finishes_xy || focusState.value?.grid_state?.finish_xy || [],
)
const agvCount = computed(() => positions.value.length)
function agvIsActive(i) { return isActiveArr.value[i] === true }
const selectedAgvPos = computed(() => positions.value[selectedAgvIndex.value] || [0, 0])
const selectedAgvActive = computed(() => agvIsActive(selectedAgvIndex.value))
const selectedAgvConfig = computed(() => store.getAGVs?.()[selectedAgvIndex.value] || null)
const selectedAgvName = computed(() =>
  selectedAgvConfig.value?.name || `AGV-${selectedAgvIndex.value}`,
)
const selectedAgvStatus = computed(() =>
  String(agvStatusArr.value[selectedAgvIndex.value] || (selectedAgvActive.value ? 'ACTIVE' : 'IDLE')).toUpperCase(),
)
const selectedAgvStatusLabel = computed(() => {
  if (selectedAgvStatus.value === 'DOWN') return '故障'
  return selectedAgvActive.value ? '执行中' : '空闲'
})
const selectedAgvRepairRemaining = computed(() =>
  Number(agvRepairArr.value[selectedAgvIndex.value] || 0),
)
const selectedAgvTarget = computed(() => agvTargets.value[selectedAgvIndex.value] || null)
const selectedAgvRuntime = computed(() => {
  const index = selectedAgvIndex.value
  const frames = store.historyBuffer || []
  let distance = 0
  let activeFrames = 0
  let totalFrames = 0
  let previous = null
  frames.forEach((frame) => {
    const position = frame.grid_state?.positions_xy?.[index]
    if (!Array.isArray(position)) return
    totalFrames += 1
    if (frame.grid_state?.is_active?.[index]) activeFrames += 1
    if (previous) distance += Math.abs(position[0] - previous[0]) + Math.abs(position[1] - previous[1])
    previous = position
  })
  return {
    activityRate: totalFrames > 0 ? `${Math.round((activeFrames / totalFrames) * 100)}%` : '—',
    distance,
    activeFrames,
    totalFrames,
  }
})

function probabilityLabel(config, probabilityKey) {
  if (!config?.enabled) return '未启用'
  let probability = Number(config[probabilityKey] || 0)
  const mtbf = Number(config.mtbf_steps || 0)
  if (!(probability > 0) && mtbf > 0) probability = 1 - Math.exp(-1 / mtbf)
  if (!(probability > 0)) return '已启用，概率未指定'
  const percentage = probability * 100
  const digits = percentage < 0.1 ? 3 : 2
  const busyOnly = config.busy_only ? '，仅工作时' : ''
  return `${percentage.toFixed(digits)}% / step${mtbf > 0 ? `（MTBF ${mtbf}）` : ''}${busyOnly}`
}

const machineFailureProbability = computed(() =>
  probabilityLabel(activeExceptionConfig.value.machine_failure, 'prob_per_machine_step'),
)
const agvFailureProbability = computed(() =>
  probabilityLabel(activeExceptionConfig.value.agv_failure, 'prob_per_agv_step'),
)

function nextScheduledEvent(type, entityKey, idField) {
  const current = currentStep.value
  const id = numericId(entityKey)
  const next = (activeExceptionConfig.value.schedule || [])
    .filter((event) => event?.type === type && Number(event.step) > current)
    .filter((event) => event[idField] == null || numericId(event[idField]) === id)
    .sort((a, b) => Number(a.step) - Number(b.step))[0]
  if (!next) return null
  return `${Number(next.step) - current} 步后（step ${next.step}）`
}

const nextMachineException = computed(() =>
  nextScheduledEvent('machine_breakdown', selectedMachine.value?.id ?? selectedMachineKey.value, 'machine_id'),
)
const nextAgvException = computed(() =>
  nextScheduledEvent('agv_breakdown', selectedAgvConfig.value?.id ?? selectedAgvIndex.value, 'agv_id'),
)

const hasAnySelection = computed(() =>
  selectedMachineKey.value != null ||
  selectedJobId.value != null ||
  selectedAgvIndex.value != null
)

// 显式可见性：默认始终显示（占位），× 关闭后变浮标
const visible = computed(() => !closed.value)
const showPill = computed(() => closed.value)

function hasSelection(tabKey) {
  if (tabKey === 'machine') return selectedMachineKey.value != null
  if (tabKey === 'job') return selectedJobId.value != null
  if (tabKey === 'agv') return selectedAgvIndex.value != null
  return false
}

function handleClose() { closed.value = true }
function reopen() { closed.value = false; pinned.value = true }

// 选中实体 → 切 tab + 弹出（覆盖 closed）
watch(selectedMachineKey, (v) => { if (v != null) { activeTab.value = 'machine'; reopen() } })
watch(selectedJobId,     (v) => { if (v != null) { activeTab.value = 'job'; reopen() } })
watch(selectedAgvIndex,  (v) => { if (v != null) { activeTab.value = 'agv'; reopen() } })

function fmtLoc(loc) {
  if (!loc) return '—'
  if (Array.isArray(loc)) return `[${loc[0]}, ${loc[1]}]`
  return String(loc)
}
</script>

<style scoped>
/* Tab 栏：sticky 固定在 DraggablePanel.dp-body 顶部，内容滚动时不消失 */
.fp-tabs {
  position: sticky;
  top: 0;
  z-index: 2;
  display: flex;
  align-items: stretch;
  background: rgba(10, 14, 28, 0.95);
  border-bottom: 1px solid rgba(255, 255, 255, 0.06);
}
.fp-tab {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 4px;
  padding: 8px 4px;
  background: none;
  border: none;
  color: #8090a0;
  cursor: pointer;
  font-size: 11px;
  transition: all .15s;
  position: relative;
}
.fp-tab:hover { color: #c0d0e0; background: rgba(255, 255, 255, 0.03); }
.fp-tab.active { color: #64b5ff; background: rgba(100, 181, 255, 0.08); }
.fp-tab.active::after {
  content: '';
  position: absolute;
  left: 12%; right: 12%; bottom: 0;
  height: 2px;
  background: #64b5ff;
  border-radius: 1px;
}
.fp-tab-icon { font-size: 13px; }
.fp-tab-label { font-weight: 600; }
.fp-dot {
  width: 5px; height: 5px;
  border-radius: 50%;
  background: #66d06a;
  margin-left: 2px;
}

/* 内容区（dp-body 已提供滚动，这里只管排版） */
.fp-content {
  padding: 10px 12px 12px;
}

.fp-head {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}
.fp-title { font-size: 14px; font-weight: 600; color: #e8eef6; }
.fp-tag {
  font-size: 10px;
  padding: 1px 6px;
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.08);
  color: #b0b8c0;
}
.tag-working { background: rgba(100, 181, 255, 0.2); color: #64b5ff; }
.tag-idle    { background: rgba(160, 160, 160, 0.18); color: #a0a0a0; }
.tag-completed { background: rgba(102, 208, 106, 0.2); color: #66d06a; }
.tag-progress  { background: rgba(100, 181, 255, 0.2); color: #64b5ff; }
.tag-broken  { background: rgba(255, 100, 100, 0.2); color: #ff6464; }
.tag-blocked { background: rgba(255, 180, 80, 0.2); color: #ffb450; }

.fp-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 3px 0;
  font-variant-numeric: tabular-nums;
}
.fp-k { color: #8090a0; }
.fp-v { color: #d0dae8; font-weight: 500; }
.fp-v-wrap {
  max-width: 150px;
  text-align: right;
  white-space: normal;
  overflow-wrap: anywhere;
}
.fp-v-danger { color: #ff7b7b; }
.fp-row-alert .fp-k,
.fp-row-alert .fp-v { color: #ff9a8f; }
.fp-empty-inline { color: #707070; font-style: italic; padding: 4px 0; }

.fp-section {
  margin-top: 10px;
  margin-bottom: 4px;
  font-size: 10px;
  color: #64b5ff;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  border-top: 1px dashed rgba(255, 255, 255, 0.06);
  padding-top: 8px;
}

.fp-progress { margin: 6px 0; }
.fp-progress-head {
  display: flex;
  justify-content: space-between;
  font-size: 10px;
  color: #9098a0;
  margin-bottom: 3px;
  font-variant-numeric: tabular-nums;
}
.fp-bar-wrap {
  height: 5px;
  background: rgba(255, 255, 255, 0.06);
  border-radius: 3px;
  overflow: hidden;
}
.fp-bar { height: 100%; border-radius: 3px; transition: width .25s; }
.bar-op  { background: linear-gradient(90deg, #64b5ff, #4a90e2); }
.bar-job { background: linear-gradient(90deg, #66d06a, #4CAF50); }

.fp-stat-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 6px;
}
.fp-stat {
  min-width: 0;
  padding: 7px 8px;
  background: rgba(100, 181, 255, 0.06);
  border-left: 2px solid rgba(100, 181, 255, 0.35);
  border-radius: 4px;
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.fp-stat strong {
  color: #e2edf8;
  font-size: 13px;
  font-variant-numeric: tabular-nums;
}
.fp-stat span {
  color: #74869a;
  font-size: 9px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

/* job op list */
.fp-op-list {
  display: flex;
  flex-direction: column;
  gap: 3px;
}
.fp-op-summary {
  display: flex;
  justify-content: space-between;
  gap: 6px;
  margin-bottom: 5px;
  color: #8494a8;
  font-size: 9px;
  font-variant-numeric: tabular-nums;
}
.fp-op-row {
  display: grid;
  grid-template-columns: 40px 70px 1fr auto;
  gap: 6px;
  align-items: center;
  padding: 3px 6px;
  border-radius: 4px;
  background: rgba(255, 255, 255, 0.03);
  font-size: 10px;
  font-variant-numeric: tabular-nums;
}
.fp-op-id { font-weight: 600; color: #c0c8d0; }
.fp-op-status { color: #8090a0; }
.fp-op-mach { color: #b0d0ff; }
.fp-op-time { color: #808890; text-align: right; }
.fp-op-row.op-finished .fp-op-status { color: #66d06a; }
.fp-op-row.op-processing .fp-op-status { color: #64b5ff; }
.fp-op-row.op-pending .fp-op-status { color: #a0a0a0; }

/* placeholder */
.fp-placeholder {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 24px 8px;
  color: #606870;
  text-align: center;
}
.fp-ph-icon { font-size: 28px; opacity: 0.5; margin-bottom: 6px; }
.fp-placeholder p { margin: 0; font-size: 11px; }

/* 收起浮标（fixed 与 DraggablePanel 对齐） */
.focus-panel-collapsed {
  position: fixed;
  top: 12px;
  right: 12px;
  width: 36px;
  height: 36px;
  border-radius: 50%;
  background: rgba(20, 26, 38, 0.92);
  backdrop-filter: blur(12px);
  border: 1px solid rgba(100, 181, 255, 0.3);
  color: #64b5ff;
  cursor: pointer;
  font-size: 16px;
  z-index: 100;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.4);
  transition: transform .15s;
}
.focus-panel-collapsed:hover { transform: scale(1.08); }
</style>
