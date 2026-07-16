<template>
  <div class="agent-panel">
    <!-- ===== 顶部 Job 状态概览 ===== -->
    <div
      class="agent-header"
      :class="{ clickable: jobList.length > 0 }"
      @click="jobList.length > 0 && (jobCollapsed = !jobCollapsed)"
    >
      <div class="agent-header-left">
        <span class="collapse-arrow" v-if="jobList.length > 0">{{ jobCollapsed ? '▶' : '▼' }}</span>
        <h3>📦 Job 状态</h3>
      </div>
      <span class="agent-counter" v-if="jobList.length > 0">
        {{ jobSummary.done }}/{{ jobSummary.total }}
        <span v-if="jobSummary.overdue > 0" class="counter-overdue">⚠️ {{ jobSummary.overdue }}</span>
      </span>
    </div>

    <div v-if="jobList.length === 0" class="agent-empty">
      <span>暂无 Job 数据</span>
    </div>
    <div v-else v-show="!jobCollapsed" class="agent-list">
      <div
        v-for="job in jobList"
        :key="job.job_id"
        class="agent-card job-card"
        :class="{ 'job-completed': job.is_completed, 'job-overdue': job.overdue, selected: job.job_id === store.selectedJobId }"
        @click="store.selectJob(job.job_id)"
      >
        <div class="agent-card-header">
          <span class="agent-icon">📦</span>
          <span class="agent-name">Job {{ job.job_id }}</span>
          <span class="job-state-tag" :class="job.stateClass">{{ job.stateLabel }}</span>
        </div>
        <div class="agent-card-body">
          <div class="agent-field">
            <span class="agent-field-label">进度</span>
            <span class="agent-field-value">
              <span class="job-progress-bar">
                <span class="job-progress-fill" :style="{ width: job.progressPct + '%' }"></span>
              </span>
              <span class="job-progress-text">{{ job.progress.done }}/{{ job.progress.total }}</span>
            </span>
          </div>
          <div class="agent-field">
            <span class="agent-field-label">Op</span>
            <span class="agent-field-value op-status-row">
              <span class="op-dot op-pending" :title="`PENDING ${job.opCount.pending}`">{{ job.opCount.pending }}</span>
              <span class="op-dot op-processing" :title="`PROCESSING ${job.opCount.processing}`">{{ job.opCount.processing }}</span>
              <span class="op-dot op-finished" :title="`FINISHED ${job.opCount.finished}`">{{ job.opCount.finished }}</span>
            </span>
          </div>
          <div class="agent-field" v-if="job.due != null">
            <span class="agent-field-label">交期</span>
            <span class="agent-field-value" :class="{ 'overdue-text': job.overdue }">t{{ job.due }}</span>
          </div>
          <div class="agent-field" v-if="job.is_completed">
            <span class="agent-field-label">完工</span>
            <span class="agent-field-value">t{{ job.completion_time }}</span>
          </div>
        </div>
      </div>
    </div>

    <!-- ===== 顶部 Machine 状态概览 ===== -->
    <div
      class="agent-header"
      :class="{ clickable: machineList.length > 0 }"
      @click="machineList.length > 0 && (machineCollapsed = !machineCollapsed)"
    >
      <div class="agent-header-left">
        <span class="collapse-arrow" v-if="machineList.length > 0">{{ machineCollapsed ? '▶' : '▼' }}</span>
        <h3>⚙️ 机器状态</h3>
      </div>
      <span class="agent-counter" v-if="machineList.length > 0">
        {{ machineSummary.working }}/{{ machineList.length }} 工作
      </span>
    </div>

    <div v-if="machineList.length === 0" class="agent-empty">
      <span>暂无机器数据</span>
    </div>
    <div v-else v-show="!machineCollapsed" class="agent-list">
      <div
        v-for="m in machineList"
        :key="m.key"
        class="agent-card machine-card"
        :class="{ selected: m.key === store.selectedMachineKey, 'machine-working': m.isWorking, 'machine-idle': !m.isWorking }"
        @click="store.selectMachine(m.key)"
      >
        <div class="agent-card-header">
          <span class="agent-icon">⚙️</span>
          <span class="agent-name">{{ m.name || m.key }}</span>
          <span class="machine-status-tag" :class="m.isWorking ? 'state-working' : 'state-idle'">{{ m.status }}</span>
        </div>
        <div class="agent-card-body">
          <div class="agent-field">
            <span class="agent-field-label">位置</span>
            <span class="agent-field-value">{{ formatLoc(m.location) }}</span>
          </div>
          <div class="agent-field">
            <span class="agent-field-label">队列</span>
            <span class="agent-field-value">{{ m.queue_length ?? 0 }}</span>
          </div>
          <div class="agent-field" v-if="m.current_op">
            <span class="agent-field-label">工序</span>
            <span class="agent-field-value">J{{ m.current_op.job_id }}-O{{ m.current_op.op_id }}</span>
          </div>
        </div>
      </div>
    </div>

    <!-- ===== 顶部 Agent 状态概览 ===== -->
    <div
      class="agent-header"
      :class="{ clickable: agvList.length > 0 }"
      @click="agvList.length > 0 && (agvCollapsed = !agvCollapsed)"
    >
      <div class="agent-header-left">
        <span class="collapse-arrow" v-if="agvList.length > 0">{{ agvCollapsed ? '▶' : '▼' }}</span>
        <h3>🤖 AGV 状态</h3>
      </div>
      <span class="agent-counter" v-if="agvList.length > 0">
        {{ activeCount }}/{{ agvList.length }} 活跃
      </span>
    </div>

    <!-- Agent 列表 -->
    <div v-if="agvList.length === 0" class="agent-empty">
      <span>暂无 Agent 数据</span>
    </div>
    <div v-else v-show="!agvCollapsed" class="agent-list">
      <div
        v-for="(agv, i) in agvList"
        :key="agv.id"
        class="agent-card"
        :class="{ active: agv._active, idle: !agv._active, selected: store.selectedAgvIndex === i }"
        @click="store.selectAgv(i)"
      >
        <div class="agent-card-header">
          <span class="agent-icon">🤖</span>
          <span class="agent-name">{{ agv.name || `AGV-${agv.id}` }}</span>
          <span class="agent-status-dot" :class="agv._active ? 'dot-active' : 'dot-idle'"></span>
        </div>
        <div class="agent-card-body">
          <div class="agent-field">
            <span class="agent-field-label">位置</span>
            <span class="agent-field-value">
              {{ agv._pos ? `(${agv._pos[0]}, ${agv._pos[1]})` : '--' }}
            </span>
          </div>
          <div class="agent-field">
            <span class="agent-field-label">速度</span>
            <span class="agent-field-value">{{ agv.velocity ?? '--' }}</span>
          </div>
          <div class="agent-field">
            <span class="agent-field-label">容量</span>
            <span class="agent-field-value">{{ agv.capacity ?? '--' }}</span>
          </div>
          <div class="agent-field">
            <span class="agent-field-label">状态</span>
            <span class="agent-field-value status-tag" :class="agv._active ? 'status-active' : 'status-idle'">
              {{ agv._active ? '运行中' : (agv.status || '空闲') }}
            </span>
          </div>
        </div>
      </div>
    </div>

    <!-- 汇总条 -->
    <div class="agent-summary" v-if="agvList.length > 0" v-show="!agvCollapsed">
      <div class="summary-item">
        <span class="summary-label">总 Agent</span>
        <span class="summary-value">{{ agvList.length }}</span>
      </div>
      <div class="summary-item">
        <span class="summary-label">活跃</span>
        <span class="summary-value active-text">{{ activeCount }}</span>
      </div>
      <div class="summary-item">
        <span class="summary-label">空闲</span>
        <span class="summary-value idle-text">{{ agvList.length - activeCount }}</span>
      </div>
    </div>

    <!-- ===== 分析区域 ===== -->
    <div class="analysis-section">
      <div class="analysis-header">
        <span class="analysis-title">💡 智能分析</span>
        <button
          class="clear-analysis-btn"
          v-if="monitorStore.agentHistory.length > 0"
          @click="monitorStore.clearAgentHistory()"
          title="清空对话"
        >×</button>
      </div>

      <!-- 预设问题模板 -->
      <div class="template-list">
        <button
          v-for="tpl in templates"
          :key="tpl.id"
          class="template-btn"
          :class="{ active: monitorStore.agentActiveTemplate === tpl.id }"
          @click="handleTemplateClick(tpl)"
          :disabled="tpl.disabled"
          :title="tpl.disabled ? '即将上线' : tpl.prompt"
        >
          <span class="tpl-icon">{{ tpl.icon }}</span>
          <span class="tpl-label">{{ tpl.label }}</span>
        </button>
      </div>

      <!-- 自定义输入 -->
      <div class="analysis-input-row">
        <input
          v-model="customQuery"
          class="analysis-input"
          placeholder="输入分析问题..."
          @keyup.enter="handleCustomQuery"
        />
        <button class="send-btn" @click="handleCustomQuery" :disabled="!customQuery.trim()">
          ▶
        </button>
      </div>

      <!-- 对话历史展示框 (持久,跨组件切换不丢) -->
      <div ref="resultBoxRef" class="analysis-result-box" :class="{ 'has-content': monitorStore.agentHistory.length > 0 }">
        <div v-if="monitorStore.agentHistory.length === 0" class="result-placeholder">
          <span v-if="isAnalyzing" class="analyzing-spinner"></span>
          <span>{{ isAnalyzing ? '正在分析中...' : '选择上方模板或输入问题，分析结果将在此展示' }}</span>
        </div>
        <div v-else class="conversation-list">
          <div
            v-for="msg in monitorStore.agentHistory"
            :key="msg.id"
            class="conversation-msg"
            :class="msg.role"
          >
            <div class="msg-role">{{ msg.role === 'user' ? '🧑 我' : '🤖 助手' }}</div>
            <div
              v-if="msg.role === 'assistant'"
              class="msg-content"
              :class="{ 'msg-error': msg.error }"
              v-html="renderMessage(msg)"
            ></div>
            <div v-else class="msg-content">{{ msg.content }}</div>
          </div>
          <div v-if="isAnalyzing && lastMessage?.streaming" class="streaming-hint">
            <span class="analyzing-spinner"></span>
            <span>生成中...</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, nextTick, watch } from 'vue'
import { useFactoryStore } from '@/stores/factory'
import { useMonitorStore } from '@/stores/monitor'
import { queryRAG } from '@/utils/rag'
import { marked } from 'marked'

const store = useFactoryStore()
const monitorStore = useMonitorStore()

// 对话框 DOM ref (自动滚到底)
const resultBoxRef = ref(null)

function scrollToBottom() {
  nextTick(() => {
    const el = resultBoxRef.value
    if (el) el.scrollTop = el.scrollHeight
  })
}

// 历史变化时自动滚到底
watch(() => monitorStore.agentHistory.length, scrollToBottom)

// ==================== Agent 状态 ====================

const agvList = computed(() => {
  const configAgvs = store.getAGVs()
  const snapshot = store.currentState
  const positions = snapshot?.grid_state?.positions_xy ?? []
  const isActive = snapshot?.grid_state?.is_active ?? []

  return configAgvs.map((agv, i) => ({
    ...agv,
    _pos: positions[i] ?? agv.initialLocation ?? null,
    _active: isActive[i] ?? false,
  }))
})

const activeCount = computed(() => agvList.value.filter(a => a._active).length)
const agvCollapsed = ref(true)  // AGV 状态区默认折叠，把空间让给对话区

// ==================== Machine 状态 ====================
// 优先用仿真快照；快照为空（仅上传地图、未启动仿真）时降级到配置中的 machines。
// 与 AGV 列表一致：始终能展示当前工厂资产，而不被"暂无数据"挡住。
function formatLoc(loc) {
  if (loc == null) return '--'
  if (Array.isArray(loc)) return `(${loc[0]}, ${loc[1]})`
  return String(loc)
}
const machineList = computed(() => {
  const snapshotMachines = store.currentState?.machines || {}
  const hasSnapshot = Object.keys(snapshotMachines).length > 0
  const configMachines = store.getCurrentAssets()?.machines || {}
  // 快照有数据时只用快照（仿真态权威）；否则降级到配置 machines（拓扑态）
  const source = hasSnapshot ? snapshotMachines : configMachines
  return Object.entries(source).map(([key, m]) => {
    const status = m.status || (m.current_op ? 'WORKING' : 'IDLE')
    return {
      key,
      name: m.name ?? store.getMachineDisplayName(m.id ?? key, store.currentState),
      status,
      isWorking: status === 'WORKING',
      current_op: m.current_op ?? null,
      queue_length: m.queue_length ?? 0,
      location: m.location ?? null,
    }
  })
})
const machineSummary = computed(() => ({
  working: machineList.value.filter(m => m.isWorking).length,
}))
const machineCollapsed = ref(true)

// ==================== Job 状态 ====================

function envTimelineStep() {
  const envTl = store.currentState?.env_timeline
  const m = String(envTl ?? '').match(/(\d+)/)
  return m ? Number(m[1]) : null
}

const jobList = computed(() => {
  // 优先用实时快照；快照为空（仅上传配置、未启动仿真）时降级到 config 中的 job_list
  // 与 machineList 降级到 getCurrentAssets().machines 行为一致
  const snapshotJobs = store.currentState?.jobs || []
  const hasSnapshot = snapshotJobs.length > 0
  const rawJobs = hasSnapshot ? snapshotJobs : jobsFromConfig()
  const stepNum = envTimelineStep()
  return rawJobs.map((job) => {
    const total = job.progress?.total ?? 0
    const done = job.progress?.done ?? 0
    const pct = total > 0 ? Math.round((done / total) * 100) : 0
    const opCount = (job.ops || []).reduce((acc, op) => {
      const k = (op.status || 'PENDING').toLowerCase()
      acc[k] = (acc[k] || 0) + 1
      return acc
    }, { pending: 0, processing: 0, finished: 0 })
    const overdue = stepNum != null && !job.is_completed && job.due != null && stepNum > job.due
    return {
      ...job,
      progressPct: pct,
      opCount,
      overdue,
      stateLabel: job.is_completed ? '已完成' : `${done}/${total}`,
      stateClass: job.is_completed ? 'state-completed' : (overdue ? 'state-overdue' : 'state-progress'),
    }
  })
})

// 把 config 里的 job_list 转成快照同结构，便于复用上面的渲染逻辑
// config: { job_id, name?, operations:[{machine_id, duration, name?}], arrival_time, due_time, priority? }
// → snapshot-like: { job_id, release, due, is_completed, completion_time, progress, ops }
function jobsFromConfig() {
  const rawJobs = store.getJobs?.() || []
  const idMap = store.getJobMachineIdMap?.() || {}
  return rawJobs.map((j) => {
    const ops = (j.operations || []).map((op, idx) => ({
      op_id: idx,
      status: 'PENDING',
      proc_time: op.duration ?? 0,
      assigned_machine: idMap[String(op.machine_id)] ?? op.machine_id,
    }))
    const total = ops.length
    return {
      job_id: j.job_id,
      name: j.name,
      release: j.arrival_time ?? 0,
      due: j.due_time ?? null,
      is_completed: false,
      completion_time: null,
      progress: { done: 0, total },
      ops,
    }
  })
}

const jobSummary = computed(() => {
  let done = 0, total = 0, overdue = 0
  jobList.value.forEach((j) => {
    total += 1
    if (j.is_completed) done += 1
    if (j.overdue) overdue += 1
  })
  return { done, total, overdue }
})

const jobCollapsed = ref(true)  // 默认折叠，与 AGV 一致

// ==================== 分析模板 ====================

const templates = [
  {
    id: 'hello',
    icon: '👋',
    label: '连通测试',
    prompt: '你好，请简单介绍一下你自己，你是什么模型，能做什么？',
    disabled: false,
  },
  {
    id: 'efficiency',
    icon: '⚡',
    label: 'AGV 效率分析',
    prompt: '请分析当前 AGV 车队的整体工作效率。包括：活跃率统计、平均负载率、空驶率估算，并给出效率评级和优化建议。',
    disabled: false,
  },
  {
    id: 'bottleneck',
    icon: '🔍',
    label: '瓶颈检测',
    prompt: '请检测当前生产线上的瓶颈节点。重点分析：机器拥堵情况、AGV 路径冲突/堆叠、物流断流现象，并给出疏通建议。',
    disabled: false,
  },
  {
    id: 'machine_load',
    icon: '📊',
    label: '机器负载均衡',
    prompt: '请分析各机器的工作负载分布。评估负载均衡性，指出过载和闲置机器，并给出负载再分配建议。',
    disabled: false,
  },
  {
    id: 'transfer_analysis',
    icon: '🚛',
    label: '运输路径分析',
    prompt: '请分析当前活跃运输任务的路径分布和 AGV 调度合理性。检查任务分配是否均衡、路径是否最优。',
    disabled: false,
  },
  {
    id: 'event_summary',
    icon: '📋',
    label: '日志事件摘要',
    prompt: '请对近期系统日志进行分类汇总。提取关键异常事件、分析错误趋势、识别高频告警类型，并给出系统健康度评估。',
    disabled: false,
  },
  {
    id: 'history_trend',
    icon: '📈',
    label: '运行趋势',
    prompt: '请分析本次运行的指标趋势变化。包括效率变化曲线、利用率波动、异常事件时间分布，判断系统运行是否稳定向好。',
    disabled: false,
  },
]

const customQuery = ref('')
const isAnalyzing = ref(false)

// 最近一条消息(用于判断 streaming 状态)
const lastMessage = computed(() => {
  const h = monitorStore.agentHistory
  return h.length > 0 ? h[h.length - 1] : null
})

// ==================== 分析逻辑 ====================

function handleTemplateClick(tpl) {
  if (tpl.disabled) return
  monitorStore.agentActiveTemplate = tpl.id
  runAnalysis(tpl.id, tpl.prompt)
}

function handleCustomQuery() {
  const q = customQuery.value.trim()
  if (!q) return
  monitorStore.agentActiveTemplate = null
  customQuery.value = ''
  runAnalysis('custom', q)
}

async function runAnalysis(type, prompt) {
  if (isAnalyzing.value) return  // 防止并发
  isAnalyzing.value = true

  // 1) 记录用户问题
  monitorStore.pushAgentMessage({ role: 'user', content: prompt, templateId: type })
  scrollToBottom()

  try {
    const currentState = store.currentState
    // hello 模板不需要上下文
    const context = type === 'hello' ? null : monitorStore.buildRAGContext(currentState)

    // 2) 流式接收 assistant 回复,chunk 直接累积进 store
    await queryRAG(prompt, context, (chunk) => {
      monitorStore.appendAgentChunk(chunk)
      scrollToBottom()
    })
    monitorStore.finalizeAgentMessage()
  } catch (err) {
    console.warn('RAG 查询失败:', err)
    monitorStore.failAgentMessage(
      '⚠ AI 服务暂不可用，请检查 RAG 配置或稍后重试。'
    )
  } finally {
    isAnalyzing.value = false
  }
}

// --- Markdown 渲染 (单条消息) ---
marked.setOptions({ breaks: true })
function renderMessage(msg) {
  if (!msg.content) return ''
  return marked.parse(msg.content)
}
</script>

<style scoped>
.agent-panel {
  display: flex;
  flex-direction: column;
  height: 100%;
  color: rgba(200, 220, 255, 0.85);
  font-size: 12px;
}

/* ==================== Agent 状态区 ==================== */

.agent-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 12px 4px;
}

.agent-header.clickable {
  cursor: pointer;
  user-select: none;
}

.agent-header.clickable:hover h3 {
  color: rgba(200, 220, 255, 1);
}

.agent-header-left {
  display: flex;
  align-items: center;
  gap: 5px;
}

.collapse-arrow {
  font-size: 9px;
  color: rgba(160, 190, 230, 0.6);
  width: 10px;
  text-align: center;
}

.agent-header h3 {
  margin: 0;
  font-size: 13px;
  font-weight: 600;
  color: rgba(200, 220, 255, 0.9);
}

.agent-counter {
  font-size: 11px;
  color: rgba(100, 180, 255, 0.7);
  background: rgba(100, 180, 255, 0.1);
  padding: 2px 8px;
  border-radius: 10px;
}

.agent-empty {
  padding: 12px;
  text-align: center;
  color: rgba(160, 190, 230, 0.4);
}

.agent-list {
  max-height: 180px;
  overflow-y: auto;
  padding: 4px 12px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.agent-list::-webkit-scrollbar {
  width: 3px;
}

.agent-list::-webkit-scrollbar-track {
  background: transparent;
}

.agent-list::-webkit-scrollbar-thumb {
  background: rgba(100, 180, 255, 0.15);
  border-radius: 2px;
}

.agent-card {
  background: rgba(100, 180, 255, 0.06);
  border: 1px solid rgba(100, 180, 255, 0.12);
  border-radius: 8px;
  padding: 6px 10px;
  cursor: pointer;
  transition: border-color 0.2s;
}

.agent-card:hover {
  border-color: rgba(100, 180, 255, 0.25);
}

.agent-card.active {
  border-left: 3px solid #4CAF50;
}

.agent-card.idle {
  border-left: 3px solid rgba(100, 180, 255, 0.2);
}

.agent-card-header {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 4px;
}

.agent-icon {
  font-size: 13px;
}

.agent-name {
  flex: 1;
  font-size: 11px;
  font-weight: 600;
  color: rgba(200, 220, 255, 0.9);
}

.agent-status-dot {
  width: 5px;
  height: 5px;
  border-radius: 50%;
}

.dot-active {
  background: #4CAF50;
  box-shadow: 0 0 4px rgba(76, 175, 80, 0.5);
}

.dot-idle {
  background: rgba(160, 190, 230, 0.3);
}

.agent-card-body {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 3px 10px;
}

.agent-field {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.agent-field-label {
  font-size: 10px;
  color: rgba(160, 190, 230, 0.45);
}

.agent-field-value {
  font-size: 10px;
  color: rgba(200, 220, 255, 0.75);
  font-variant-numeric: tabular-nums;
}

.status-tag {
  padding: 1px 5px;
  border-radius: 3px;
  font-size: 9px;
  font-weight: 600;
}

.status-active {
  background: rgba(76, 175, 80, 0.15);
  color: #4CAF50;
}

.status-idle {
  background: rgba(160, 190, 230, 0.1);
  color: rgba(160, 190, 230, 0.45);
}

.agent-summary {
  display: flex;
  gap: 6px;
  padding: 6px 12px;
  border-top: 1px solid rgba(100, 180, 255, 0.08);
  border-bottom: 1px solid rgba(100, 180, 255, 0.08);
  background: rgba(100, 180, 255, 0.03);
  flex-shrink: 0;
}

/* ==================== Job 卡片（沿用 agent-card 风格） ==================== */

.counter-overdue {
  margin-left: 4px;
  color: #ff6464;
}

.job-card.selected {
  border-color: rgba(102, 208, 106, 0.55);
  box-shadow: 0 0 0 2px rgba(102, 208, 106, 0.18);
}
.job-card.job-completed {
  opacity: 0.65;
}
.job-card.job-overdue {
  border-left: 3px solid rgba(255, 100, 100, 0.7);
}

/* machine card 选中态（与 FocusPanel 高亮色一致） */
.machine-card.selected {
  border-color: rgba(100, 181, 255, 0.55);
  box-shadow: 0 0 0 2px rgba(100, 181, 255, 0.2);
}
.machine-card.machine-working { border-left: 3px solid rgba(100, 181, 255, 0.6); }
.machine-card.machine-idle    { border-left: 3px solid rgba(160, 160, 160, 0.25); }

/* machine 状态 pill（风格对齐 job-state-tag，但语义独立） */
.machine-status-tag {
  margin-left: auto;
  padding: 1px 6px;
  border-radius: 8px;
  font-size: 9px;
  font-weight: 600;
  background: rgba(255, 255, 255, 0.08);
  color: rgba(200, 220, 255, 0.7);
  font-variant-numeric: tabular-nums;
}
.machine-status-tag.state-working { background: rgba(100, 181, 255, 0.2); color: #64b5ff; }
.machine-status-tag.state-idle    { background: rgba(160, 160, 160, 0.18); color: #a0a0a0; }

/* AGV 卡片选中态（与 machine/job 一致的高亮） */
.agent-card.selected {
  border-color: rgba(100, 181, 255, 0.55);
  box-shadow: 0 0 0 2px rgba(100, 181, 255, 0.2);
}

.job-state-tag {
  margin-left: auto;
  padding: 1px 6px;
  border-radius: 8px;
  font-size: 9px;
  font-weight: 600;
  background: rgba(255, 255, 255, 0.08);
  color: rgba(200, 220, 255, 0.7);
}
.job-state-tag.state-completed { background: rgba(102, 208, 106, 0.2); color: #66d06a; }
.job-state-tag.state-progress  { background: rgba(100, 181, 255, 0.2); color: #64b5ff; }
.job-state-tag.state-overdue   { background: rgba(255, 100, 100, 0.2); color: #ff6464; }

.job-progress-bar {
  display: inline-block;
  width: 42px;
  height: 4px;
  background: rgba(255, 255, 255, 0.08);
  border-radius: 2px;
  overflow: hidden;
  vertical-align: middle;
  margin-right: 4px;
}
.job-progress-fill {
  display: block;
  height: 100%;
  background: linear-gradient(90deg, #66d06a, #4CAF50);
  transition: width 0.2s;
}
.job-progress-text {
  font-size: 9px;
  color: rgba(200, 220, 255, 0.75);
  font-variant-numeric: tabular-nums;
}

.op-status-row {
  display: inline-flex;
  gap: 3px;
}
.op-dot {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 12px;
  height: 12px;
  padding: 0 3px;
  border-radius: 3px;
  font-size: 8px;
  font-weight: 600;
  font-variant-numeric: tabular-nums;
}
.op-dot.op-pending   { background: rgba(160, 160, 160, 0.18); color: #a0a0a0; }
.op-dot.op-processing{ background: rgba(100, 181, 255, 0.25); color: #64b5ff; }
.op-dot.op-finished  { background: rgba(102, 208, 106, 0.22); color: #66d06a; }

.overdue-text { color: #ff6464; }

.summary-item {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 1px;
}

.summary-label {
  font-size: 9px;
  color: rgba(160, 190, 230, 0.45);
}

.summary-value {
  font-size: 13px;
  font-weight: 700;
  color: rgba(200, 220, 255, 0.9);
  font-variant-numeric: tabular-nums;
}

.active-text { color: #4CAF50; }
.idle-text { color: rgba(160, 190, 230, 0.45); }

/* ==================== 分析区域 ==================== */

.analysis-section {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-height: 0;
  padding: 8px 12px 10px;
  gap: 6px;
}

.analysis-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.analysis-title {
  font-size: 12px;
  font-weight: 600;
  color: rgba(200, 220, 255, 0.9);
}

.clear-analysis-btn {
  background: none;
  border: none;
  color: rgba(160, 190, 230, 0.4);
  font-size: 14px;
  cursor: pointer;
  padding: 0 2px;
  line-height: 1;
}

.clear-analysis-btn:hover {
  color: rgba(200, 220, 255, 0.8);
}

/* 模板按钮 */
.template-list {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}

.template-btn {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 4px 8px;
  border: 1px solid rgba(100, 180, 255, 0.12);
  border-radius: 6px;
  background: rgba(100, 180, 255, 0.04);
  color: rgba(200, 220, 255, 0.7);
  font-size: 10px;
  cursor: pointer;
  transition: all 0.15s;
  white-space: nowrap;
}

.template-btn:hover:not(:disabled) {
  background: rgba(100, 180, 255, 0.1);
  border-color: rgba(100, 180, 255, 0.25);
  color: rgba(200, 220, 255, 0.95);
}

.template-btn.active {
  background: rgba(100, 180, 255, 0.15);
  border-color: rgba(100, 180, 255, 0.35);
  color: rgba(200, 220, 255, 0.95);
}

.template-btn:disabled {
  opacity: 0.35;
  cursor: not-allowed;
}

.tpl-icon {
  font-size: 11px;
}

.tpl-label {
  font-size: 10px;
  font-weight: 500;
}

/* 输入行 */
.analysis-input-row {
  display: flex;
  gap: 4px;
}

.analysis-input {
  flex: 1;
  padding: 5px 8px;
  border: 1px solid rgba(100, 180, 255, 0.12);
  border-radius: 6px;
  background: rgba(20, 25, 45, 0.5);
  color: rgba(200, 220, 255, 0.9);
  font-size: 11px;
  outline: none;
  transition: border-color 0.2s;
}

.analysis-input::placeholder {
  color: rgba(160, 190, 230, 0.3);
}

.analysis-input:focus {
  border-color: rgba(100, 180, 255, 0.3);
}

.send-btn {
  padding: 4px 10px;
  border: 1px solid rgba(100, 180, 255, 0.2);
  border-radius: 6px;
  background: rgba(100, 180, 255, 0.1);
  color: rgba(200, 220, 255, 0.8);
  font-size: 11px;
  cursor: pointer;
  transition: all 0.15s;
}

.send-btn:hover:not(:disabled) {
  background: rgba(100, 180, 255, 0.2);
  color: rgba(200, 220, 255, 1);
}

.send-btn:disabled {
  opacity: 0.35;
  cursor: not-allowed;
}

/* 分析结果展示框 */
.analysis-result-box {
  flex: 1;
  min-height: 120px;
  overflow-y: auto;
  user-select: text;
  -webkit-user-select: text;
  padding: 8px 10px;
  border: 1px solid rgba(100, 180, 255, 0.08);
  border-radius: 8px;
  background: rgba(10, 14, 28, 0.5);
  line-height: 1.5;
}

.analysis-result-box.has-content {
  border-color: rgba(100, 180, 255, 0.15);
}

.analysis-result-box::-webkit-scrollbar {
  width: 3px;
}

.analysis-result-box::-webkit-scrollbar-track {
  background: transparent;
}

.analysis-result-box::-webkit-scrollbar-thumb {
  background: rgba(100, 180, 255, 0.15);
  border-radius: 2px;
}

.result-placeholder {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  height: 100%;
  min-height: 60px;
  color: rgba(160, 190, 230, 0.25);
  font-size: 11px;
  text-align: center;
}

.analyzing-spinner {
  display: inline-block;
  width: 12px;
  height: 12px;
  border: 2px solid rgba(100, 180, 255, 0.2);
  border-top-color: rgba(100, 180, 255, 0.6);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

/* ==================== 对话历史 ==================== */
.conversation-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 2px;
}

.conversation-msg {
  display: flex;
  flex-direction: column;
  gap: 3px;
}

.conversation-msg.user {
  align-items: flex-end;
}

.conversation-msg.user .msg-content {
  background: rgba(100, 180, 255, 0.08);
  border-left: 2px solid rgba(100, 180, 255, 0.4);
  padding: 5px 8px;
  border-radius: 6px;
  max-width: 90%;
  white-space: pre-wrap;
}

.conversation-msg.assistant .msg-content {
  background: rgba(255, 255, 255, 0.02);
  padding: 2px 0;
}

.msg-role {
  font-size: 10px;
  color: rgba(160, 190, 230, 0.45);
  font-weight: 500;
}

.conversation-msg.user .msg-role {
  text-align: right;
}

.msg-content.msg-error {
  color: rgba(255, 150, 150, 0.85);
}

.streaming-hint {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 4px 2px;
  color: rgba(160, 190, 230, 0.5);
  font-size: 10px;
}

.msg-content {
  font-size: 11px;
  color: rgba(200, 220, 255, 0.8);
  word-break: break-word;
  line-height: 1.6;
}

/* Markdown 元素样式 */
.msg-content :deep(p) {
  margin: 4px 0;
}

.msg-content :deep(h1),
.msg-content :deep(h2),
.msg-content :deep(h3),
.msg-content :deep(h4) {
  margin: 8px 0 4px;
  color: rgba(200, 220, 255, 0.95);
  font-weight: 600;
  line-height: 1.3;
}

.msg-content :deep(h1) { font-size: 14px; }
.msg-content :deep(h2) { font-size: 13px; }
.msg-content :deep(h3) { font-size: 12px; }
.msg-content :deep(h4) { font-size: 11px; }

.msg-content :deep(ul),
.msg-content :deep(ol) {
  margin: 4px 0;
  padding-left: 18px;
}

.msg-content :deep(li) {
  margin: 2px 0;
}

.msg-content :deep(code) {
  background: rgba(100, 180, 255, 0.1);
  padding: 1px 4px;
  border-radius: 3px;
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
  font-size: 10px;
  color: rgba(180, 220, 255, 0.95);
}

.msg-content :deep(pre) {
  background: rgba(10, 14, 28, 0.6);
  border: 1px solid rgba(100, 180, 255, 0.12);
  border-radius: 6px;
  padding: 8px 10px;
  margin: 6px 0;
  overflow-x: auto;
}

.msg-content :deep(pre code) {
  background: none;
  padding: 0;
  font-size: 10px;
}

.msg-content :deep(blockquote) {
  border-left: 3px solid rgba(100, 180, 255, 0.3);
  margin: 6px 0;
  padding: 2px 10px;
  color: rgba(160, 190, 230, 0.7);
}

.msg-content :deep(table) {
  border-collapse: collapse;
  margin: 6px 0;
  font-size: 10px;
}

.msg-content :deep(th),
.msg-content :deep(td) {
  border: 1px solid rgba(100, 180, 255, 0.15);
  padding: 3px 6px;
  text-align: left;
}

.msg-content :deep(th) {
  background: rgba(100, 180, 255, 0.08);
  font-weight: 600;
}

.msg-content :deep(strong) {
  color: rgba(200, 220, 255, 0.95);
  font-weight: 600;
}

.msg-content :deep(.tag-ok) {
  color: rgba(76, 175, 80, 0.9);
}

.msg-content :deep(.tag-warn) {
  color: rgba(255, 152, 0, 0.9);
}

.msg-content :deep(.tag-info) {
  color: rgba(100, 180, 255, 0.8);
}
</style>
