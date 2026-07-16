<template>
  <div class="job-insert-panel">
    <div class="mode-tabs" role="tablist">
      <button :class="{ active: mode === 'quick' }" @click="mode = 'quick'">快速插单</button>
      <button :class="{ active: mode === 'json' }" @click="mode = 'json'">JSON 批量上传</button>
    </div>

    <div v-if="disabledReason" class="notice">{{ disabledReason }}</div>

    <form v-if="mode === 'quick'" class="quick-form" @submit.prevent="submitQuick">
      <div class="form-grid">
        <label>订单名称<input v-model.trim="quick.name" maxlength="40" required /></label>
        <label>优先级
          <select v-model.number="quick.priority">
            <option :value="100">高（不抢占）</option><option :value="200">特急（可暂停非特急）</option>
          </select>
        </label>
        <label title="从插单请求受理时的仿真 step 开始计算">相对交期（受理后 step）
          <input v-model.number="quick.dueInSteps" type="number" min="1" placeholder="可选" />
        </label>
      </div>

      <div class="section-head">
        <span>工序</span><button type="button" class="small-btn" @click="addOperation">+ 添加工序</button>
      </div>
      <div v-for="(op, opIndex) in quick.operations" :key="op.id" class="operation-block">
        <div class="operation-title">
          <strong>工序 {{ opIndex + 1 }}</strong>
          <button v-if="quick.operations.length > 1" type="button" class="icon-btn" title="删除工序" @click="removeOperation(opIndex)">x</button>
        </div>
        <div class="candidate-header"><span></span><span>候选设备</span><span>加工时间（step）</span></div>
        <div class="candidate-list">
          <label v-for="machine in machineOptions" :key="machine.id" class="candidate-row">
            <input v-model="op.selected" type="checkbox" :value="machine.id" />
            <span>{{ machine.name }}</span>
            <input v-model.number="op.times[machine.id]" type="number" min="1" step="1" :disabled="!op.selected.includes(machine.id)" />
          </label>
        </div>
      </div>
      <button class="primary-btn" :disabled="submitDisabled" type="submit">{{ submitting ? '提交中...' : '提交紧急订单' }}</button>
    </form>

    <div v-else class="json-pane">
      <div class="drop-zone" :class="{ active: isDragging }" @click="fileInputRef?.click()"
           @dragover.prevent="isDragging = true" @dragleave.prevent="isDragging = false" @drop.prevent="handleDrop">
        <input ref="fileInputRef" type="file" accept=".json,application/json" hidden @change="handleFileSelect" />
        <strong>选择或拖入 FJSP v2 JSON</strong>
        <span>最多 20 个 Job，每个 Job 最多 20 道工序</span>
      </div>
      <div v-if="parseError" class="result error">{{ parseError }}</div>
      <div v-if="parsed" class="file-summary">
        <span>{{ parsed.jobs.length }} Jobs</span><span>{{ parsed.machines }} 台机器</span>
        <span>{{ parsed.jobs.reduce((n, job) => n + job.length, 0) }} 道工序</span>
      </div>
      <div class="action-row">
        <button class="primary-btn" :disabled="submitDisabled || !parsed" @click="submitBody(parsed)">{{ submitting ? '提交中...' : '提交批量插单' }}</button>
        <button class="ghost-btn" :disabled="submitting" @click="resetJson">清空</button>
      </div>
    </div>

    <div v-if="lastResult" class="result" :class="lastResult.status">
      <strong>{{ lastResult.status === 'ok' ? '已受理' : lastResult.status === 'partial' ? '部分受理' : '提交失败' }}</strong>
      <span>{{ lastResult.message || (lastResult.request_id ? `请求 ${lastResult.request_id}` : '') }}</span>
      <span v-for="item in lastResult.rejected || []" :key="item.index">Job {{ item.index }}：{{ item.reason || item.message }}</span>
    </div>

    <div class="records">
      <div class="section-head"><span>本次运行插单记录</span><span class="count">{{ insertionRecords.length }}</span></div>
      <div v-if="!insertionRecords.length" class="empty">暂无插单记录</div>
      <article v-for="record in insertionRecords" :key="record.request_id" class="record">
        <div class="record-head">
          <strong>{{ record.inserted?.map(item => item.name).join('、') || record.request_id }}</strong>
          <span class="phase" :class="record.phase">{{ phaseLabel(record.phase) }}</span>
        </div>
        <div class="meta">
          <span>{{ record.request_id }}</span><span>Job {{ record.job_ids?.join(', ') }}</span><span>step {{ record.accepted_step }}</span>
          <span v-if="record.revision">版本 {{ record.revision }}</span><span v-if="record.latency_ms != null">{{ Math.round(record.latency_ms) }} ms</span>
        </div>
        <div class="timeline">
          <span v-for="phase in phases" :key="phase" :class="{ reached: reachedPhase(record, phase) }">{{ phaseLabel(phase) }}</span>
        </div>
        <div class="progress">工序进度 {{ recordProgress(record).done }}/{{ recordProgress(record).total }}</div>
        <div v-if="record.error" class="failure">{{ record.error }}</div>
      </article>
    </div>
  </div>
</template>

<script setup>
import { computed, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { useFactoryStore } from '@/stores/factory'
import { apiPost, API_ROUTES } from '@/utils/api'

const props = defineProps({
  isRunning: { type: Boolean, default: false },
  algorithm: { type: String, default: '' },
  supportsInsertion: { type: Boolean, default: false },
})
const store = useFactoryStore()
const mode = ref('quick')
const submitting = ref(false)
const parsed = ref(null)
const parseError = ref('')
const lastResult = ref(null)
const fileInputRef = ref(null)
const isDragging = ref(false)
let operationId = 1
const quick = reactive({ name: '', priority: 100, dueInSteps: null, operations: [] })
const phases = ['queued', 'replanning', 'scheduled', 'transporting', 'processing', 'completed']
const phaseOrder = Object.fromEntries(phases.map((phase, index) => [phase, index]))

const machineOptions = computed(() => {
  const live = Object.values(store.latestState?.machines || {})
  if (live.length) return live.map((m, index) => ({ id: Number(m.runtime_id ?? m.id ?? index), name: m.display_name || m.name || `M${index}` }))
  return Object.values(store.currentTopologyConfig?.machines || {}).map((m, index) => ({ id: index, name: m.name || m.id || `M${index}` }))
})
const insertionRecords = computed(() => store.currentState?.insertion_requests || [])
const disabledReason = computed(() => {
  if (!props.supportsInsertion) return '当前工厂不支持真实插单'
  if (!props.isRunning) return '仿真启动后才可提交插单'
  const parts = props.algorithm.toLowerCase().split('+')
  if (parts[0] !== 'pso') return `当前 FJSP 算法为 ${parts[0] || '未知'}，第一版仅支持 PSO`
  if (parts[2] !== 'nearest') return `当前指派器为 ${parts[2] || '未知'}，第一版仅支持 nearest`
  return ''
})
const submitDisabled = computed(() => submitting.value || Boolean(disabledReason.value))

function addOperation() {
  const first = machineOptions.value[0]?.id
  quick.operations.push({ id: operationId++, selected: first == null ? [] : [first], times: first == null ? {} : { [first]: 5 } })
}
function removeOperation(index) { quick.operations.splice(index, 1) }
addOperation()

function validateFjspBody(data) {
  if (!data || typeof data !== 'object' || Array.isArray(data)) throw new Error('文件内容必须是 JSON 对象')
  if (!Number.isInteger(data.machines) || data.machines <= 0) throw new Error('machines 必须是正整数')
  if (data.machines !== machineOptions.value.length) throw new Error(`机器数应为 ${machineOptions.value.length}`)
  if (!Array.isArray(data.jobs) || !data.jobs.length || data.jobs.length > 20) throw new Error('jobs 数量必须为 1~20')
  data.jobs.forEach((job, jobIndex) => {
    if (!Array.isArray(job) || !job.length || job.length > 20) throw new Error(`Job ${jobIndex} 的工序数必须为 1~20`)
    job.forEach((op, opIndex) => {
      if (!Array.isArray(op) || !op.length) throw new Error(`Job ${jobIndex} 工序 ${opIndex} 缺少候选机器`)
      const seen = new Set()
      op.forEach((alt) => {
        if (!Number.isInteger(alt?.machine) || alt.machine < 0 || alt.machine >= data.machines) throw new Error(`Job ${jobIndex} 工序 ${opIndex} 的机器编号非法`)
        if (seen.has(alt.machine)) throw new Error(`Job ${jobIndex} 工序 ${opIndex} 包含重复机器`)
        if (typeof alt.processing !== 'number' || !Number.isFinite(alt.processing) || alt.processing <= 0) throw new Error(`Job ${jobIndex} 工序 ${opIndex} 的加工时间非法`)
        seen.add(alt.machine)
      })
    })
  })
  const metadata = data.extensions?.job_metadata
  if (metadata != null && (!Array.isArray(metadata) || metadata.length !== data.jobs.length)) throw new Error('job_metadata 必须与 jobs 一一对应')
  return { machines: data.machines, jobs: data.jobs, extensions: data.extensions || {} }
}

function submitQuick() {
  try {
    if (!quick.name) throw new Error('请填写订单名称')
    const jobs = [quick.operations.map((op, index) => {
      if (!op.selected.length) throw new Error(`工序 ${index + 1} 至少选择一台候选机器`)
      return op.selected.map((machine) => {
        const processing = Number(op.times[machine])
        if (!Number.isInteger(processing) || processing <= 0) throw new Error(`工序 ${index + 1} 的加工时间必须是正整数 step`)
        return { machine, processing }
      })
    })]
    const meta = { name: quick.name, priority: quick.priority }
    if (quick.dueInSteps != null && quick.dueInSteps !== '') meta.due_in_steps = Number(quick.dueInSteps)
    submitBody(validateFjspBody({ machines: machineOptions.value.length, jobs, extensions: { job_metadata: [meta] } }))
  } catch (error) { ElMessage.error(error.message) }
}

async function submitBody(body) {
  if (submitDisabled.value || !body) return
  submitting.value = true
  try {
    const response = await apiPost(API_ROUTES.FACTORY_CONTROL_INSERT_JOBS, body, { timeout: 30000 })
    lastResult.value = response
    if (response.status === 'ok') ElMessage.success('紧急订单已进入重规划队列')
    else if (response.status === 'partial') ElMessage.warning('部分 Job 已进入重规划队列')
    else ElMessage.error(response.message || '插单失败')
  } catch (error) {
    lastResult.value = { status: 'error', message: error.message, rejected: [] }
    ElMessage.error('插单请求失败')
  } finally { submitting.value = false }
}

function readFile(file) {
  parseError.value = ''
  const reader = new FileReader()
  reader.onload = () => {
    try { parsed.value = validateFjspBody(JSON.parse(reader.result)) }
    catch (error) { parsed.value = null; parseError.value = error.message }
  }
  reader.onerror = () => { parsed.value = null; parseError.value = '文件读取失败' }
  reader.readAsText(file)
}
function handleFileSelect(event) { const file = event.target.files?.[0]; event.target.value = ''; if (file) readFile(file) }
function handleDrop(event) { isDragging.value = false; const file = event.dataTransfer.files?.[0]; if (file) readFile(file) }
function resetJson() { parsed.value = null; parseError.value = ''; lastResult.value = null }
function phaseLabel(phase) { return ({ queued: '排队', replanning: '重规划', scheduled: '已排程', transporting: '运输中', processing: '加工中', completed: '已完成', failed: '失败' })[phase] || phase }
function reachedPhase(record, phase) { return record.phase === 'failed' ? (record.timeline || []).some(item => item.phase === phase) : phaseOrder[phase] <= (phaseOrder[record.phase] ?? -1) }
function recordProgress(record) {
  const ids = new Set(record.job_ids || [])
  return (store.currentState?.jobs || []).filter(job => ids.has(job.job_id)).reduce((sum, job) => ({ done: sum.done + (job.progress?.done || 0), total: sum.total + (job.progress?.total || 0) }), { done: 0, total: 0 })
}
</script>

<style scoped>
.job-insert-panel { display:flex; flex-direction:column; gap:12px; padding:12px 10px; color:#dce6f5; font-size:12px; }
.mode-tabs { display:grid; grid-template-columns:1fr 1fr; border:1px solid rgba(130,160,195,.22); border-radius:6px; overflow:hidden; }
.mode-tabs button { padding:8px; border:0; background:#172033; color:#91a6c2; cursor:pointer; }
.mode-tabs button.active { background:#2d6f78; color:#fff; }
.notice { padding:8px 10px; border-left:3px solid #d99b3d; background:rgba(217,155,61,.11); color:#f2c77f; }
.quick-form,.json-pane { display:flex; flex-direction:column; gap:10px; }
.form-grid { display:grid; grid-template-columns:2fr 1fr; gap:8px; }
.form-grid label:last-child { grid-column:1 / -1; }
label { display:flex; flex-direction:column; gap:4px; color:#9fb2ca; }
input,select { box-sizing:border-box; min-width:0; padding:6px 7px; border:1px solid rgba(145,175,210,.22); border-radius:4px; background:#11192a; color:#e8eef7; }
.section-head,.operation-title,.record-head,.meta,.action-row { display:flex; align-items:center; justify-content:space-between; gap:8px; }
.section-head { padding-top:7px; border-top:1px solid rgba(255,255,255,.08); color:#7fc1c6; font-weight:600; }
.small-btn,.icon-btn,.ghost-btn { border:1px solid rgba(145,175,210,.2); background:transparent; color:#aec1d8; border-radius:4px; cursor:pointer; }
.small-btn { padding:4px 8px; }.icon-btn { width:24px; height:24px; }
.operation-block { padding:8px; border:1px solid rgba(145,175,210,.14); border-radius:6px; background:rgba(17,25,42,.7); }
.candidate-list { display:grid; gap:4px; margin-top:7px; }
.candidate-header { display:grid; grid-template-columns:18px 1fr 76px; gap:7px; margin-top:7px; color:#70859f; font-size:10px; }
.candidate-row { display:grid; grid-template-columns:18px 1fr 76px; align-items:center; gap:7px; }
.candidate-row input[type=checkbox] { width:14px; height:14px; }
.primary-btn { padding:8px 12px; border:1px solid #3d8f96; border-radius:5px; background:#28747a; color:white; font-weight:600; cursor:pointer; }
.primary-btn:disabled,.ghost-btn:disabled { opacity:.4; cursor:not-allowed; }.ghost-btn { padding:8px 12px; }
.drop-zone { display:flex; flex-direction:column; align-items:center; gap:5px; padding:22px 12px; border:1px dashed rgba(110,180,190,.45); border-radius:6px; background:#131d2e; cursor:pointer; }
.drop-zone.active { border-color:#6fc4c9; background:#172b38; }.drop-zone span,.empty { color:#7f94ae; }
.file-summary { display:flex; gap:12px; padding:8px; background:#151f31; }.action-row .primary-btn { flex:1; }
.result { display:flex; flex-direction:column; gap:4px; padding:8px 10px; border-left:3px solid #6ba7b0; background:#141f31; }
.result.error { border-color:#d66b6b; color:#f2aaaa; }.result.partial { border-color:#d6a34f; }
.records { display:flex; flex-direction:column; gap:7px; }.count { min-width:20px; text-align:center; padding:1px 5px; border-radius:10px; background:#21364a; }
.record { padding:9px; border:1px solid rgba(145,175,210,.15); border-radius:6px; background:#121b2b; }
.record-head strong { overflow-wrap:anywhere; }.phase { padding:2px 6px; border-radius:3px; background:#29455b; white-space:nowrap; }.phase.completed { background:#28614d; }.phase.failed { background:#6b3035; }
.meta { justify-content:flex-start; flex-wrap:wrap; margin-top:6px; color:#8498b1; font-size:10px; }
.timeline { display:grid; grid-template-columns:repeat(6,1fr); gap:3px; margin-top:8px; }
.timeline span { padding:3px 1px; text-align:center; color:#677b94; border-top:2px solid #29374a; font-size:9px; }.timeline span.reached { color:#a8d8db; border-color:#4ca0a7; }
.progress { margin-top:7px; color:#a9b9cc; }.failure { margin-top:5px; color:#ef9b9b; overflow-wrap:anywhere; }
@media (max-width:420px) { .form-grid { grid-template-columns:1fr; }.form-grid label:last-child { grid-column:auto; }.timeline { grid-template-columns:repeat(3,1fr); } }
</style>
