<template>
  <DraggablePanel
    icon="📊"
    title="批处理实验"
    :width="1080"
    :height="640"
    :initial-pos="{ x: 120, y: 60 }"
    @close="ui.closeBatch()"
  >
    <div class="batch-panel">
      <div class="batch-body">
        <!-- ============ 左栏：配置表单 ============ -->
        <div class="panel form-panel">
          <div class="panel-title">实验配置</div>

          <div class="form-row">
            <label>FJSP 调度算法</label>
            <select v-model="form.fjsp_algo" class="plan-select">
              <option v-for="a in fjspAlgorithms" :key="a.id" :value="a.id">
                {{ a.name }} ({{ fjspImage(a.id) }})
              </option>
            </select>
          </div>

          <div class="form-row">
            <label>MAPF 路由算法</label>
            <select v-model="form.mapf_algo" class="plan-select">
              <option v-for="a in mapfAlgorithms" :key="a.id" :value="a.id">
                {{ a.name }} ({{ mapfImage(a.id) }})
              </option>
            </select>
          </div>

          <div class="form-row">
            <label>观测类型 (OBS_TYPE)</label>
            <select v-model="form.mapf_obs_type" class="plan-select">
              <option value="default">default (全观测)</option>
              <option value="MAPF">MAPF (全局路由观测)</option>
              <option value="POMAPF">POMAPF (部分可观测)</option>
            </select>
          </div>

          <div class="form-row">
            <label>随机种子（每个种子跑一次 run.py）</label>
            <input v-model="form.seedsText" placeholder="1, 2, 3" />
            <div class="hint">将运行 <b>{{ experimentsPreview.length }}</b> 次实验</div>
          </div>

          <!-- 实例上传 -->
          <div class="panel-subtitle">实例文件（可选）</div>
          <div class="upload-row">
            <div class="upload-label">
              <span>FJSP</span>
              <span class="upload-current" :class="{ set: form.fjsp_instance }">
                {{ form.fjsp_instance || '默认 J10P5M6.json' }}
              </span>
            </div>
            <label class="upload-btn">
              上传 .json
              <input
                type="file"
                accept=".json,application/json"
                hidden
                @change="(e) => onUpload(e, 'fjsp')"
              />
            </label>
            <button v-if="form.fjsp_instance" class="clear-btn" @click="form.fjsp_instance = ''">清除</button>
          </div>
          <div class="upload-row">
            <div class="upload-label">
              <span>MAPF</span>
              <span class="upload-current" :class="{ set: form.mapf_instance }">
                {{ form.mapf_instance || '默认 medium-mazes-seed-0000@medium_maps.yaml' }}
              </span>
            </div>
            <label class="upload-btn">
              上传 .yaml
              <input
                type="file"
                accept=".yaml,.yml"
                hidden
                @change="(e) => onUpload(e, 'mapf')"
              />
            </label>
            <button v-if="form.mapf_instance" class="clear-btn" @click="form.mapf_instance = ''">清除</button>
          </div>

          <!-- 操作 -->
          <div class="action-row">
            <button class="primary-btn" :disabled="!canStart" @click="start">
              {{ running ? '运行中…' : `运行 ${experimentsPreview.length} 次实验` }}
            </button>
            <button class="danger-btn" :disabled="!running" @click="cancel">取消</button>
          </div>
        </div>

        <!-- ============ 右栏：运行区 ============ -->
        <div class="panel run-panel">
          <div class="panel-title">
            运行状态
            <span v-if="running" class="status-tag running">RUNNING {{ status.idx }}/{{ status.total }}</span>
            <span v-else-if="status.cancelled" class="status-tag cancelled">CANCELLED</span>
            <span v-else-if="status.done" class="status-tag done">DONE</span>
            <span v-else class="status-tag idle">IDLE</span>
          </div>

          <!-- 进度条 -->
          <div class="progress-bar">
            <div class="progress-fill" :style="{ width: progressPercent + '%' }"></div>
          </div>

          <!-- 日志 -->
          <div class="panel-subtitle">
            实时日志
            <span class="hint">{{ logs.length }} 行</span>
          </div>
          <div ref="logBoxRef" class="log-box">
            <div
              v-for="l in logs"
              :key="l.id"
              class="log-line"
              :class="{ err: l.isErr }"
              v-memo="[l.text, l.isErr]"
            >
              {{ l.text }}
            </div>
            <div v-if="!logs.length" class="log-empty">（暂无日志，启动后此处实时显示 run.py stdout）</div>
          </div>

          <!-- 结果表 -->
          <div class="panel-subtitle">
            结果汇总
            <span class="hint">{{ results.length }} / {{ status.total || experimentsPreview.length }}</span>
          </div>
          <div class="result-table-wrap">
            <table v-if="results.length" class="result-table">
              <thead>
                <tr>
                  <th>#</th>
                  <th>seed</th>
                  <th>job/route</th>
                  <th>makespan</th>
                  <th>full_ms</th>
                  <th>success</th>
                  <th>machine_util</th>
                  <th>agv_load_util</th>
                  <th>reason</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="r in results" :key="r.run_id" :class="{ err: r.terminated_reason === 'error' }">
                  <td>{{ r.run_id }}</td>
                  <td>{{ r.cfg?.seed ?? '-' }}</td>
                  <td class="mono small">{{ r.cfg?.solver_job }}/{{ r.cfg?.solver_route }}</td>
                  <td>{{ fmt(r.metrics?.completed_makespan) }}</td>
                  <td>{{ fmt(r.metrics?.full_makespan) }}</td>
                  <td>{{ fmt(r.metrics?.success_rate, true) }}</td>
                  <td>{{ fmt(r.metrics?.machine_utilization, true) }}</td>
                  <td>{{ fmt(r.metrics?.agv_loaded_utilization, true) }}</td>
                  <td>{{ r.terminated_reason || r.metrics?.terminated_reason || '-' }}</td>
                </tr>
              </tbody>
            </table>
            <div v-else class="log-empty">（暂无结果）</div>
          </div>
        </div>
      </div>
    </div>
  </DraggablePanel>
</template>

<script setup>
import { ref, reactive, computed, onBeforeUnmount, shallowRef, nextTick } from 'vue'
import { ElMessage } from 'element-plus'
import DraggablePanel from './DraggablePanel.vue'
import { useUiPanelStore } from '@/stores/uiPanel'
import { getAllAlgorithms } from '@/config/algorithms'
import { apiPost, apiGet, getApiUrl, API_ROUTES } from '@/utils/api'

const ui = useUiPanelStore()

// ============ 算法池数据（镜像名映射对齐后端 ALGORITHM_MAP）============
const { fjsp: fjspAlgorithms, mapf: mapfAlgorithms } = getAllAlgorithms()

// 算法 id → 镜像名（与后端 DockerProxy.ALGORITHM_MAP 一致）
function fjspImage(id) { return `skyengine-fjsp-${id}:latest` }
function mapfImage(id) { return `skyengine-mapf-${id}:latest` }

// ============ 表单 ============
// SOLVER_JOB / SOLVER_ROUTE 固定为 http（exp0503 模式：通过 HTTP 调算法容器）
const form = reactive({
  fjsp_algo: 'pso',       // FJSP 调度算法 id（决定 fjsp_image）
  mapf_algo: 'astar',     // MAPF 路由算法 id（决定 mapf_image）
  mapf_obs_type: 'default',
  seedsText: '1, 2, 3',   // 默认 3 个种子，跑 3 次实验取统计
  fjsp_instance: '',
  mapf_instance: '',
})

const seeds = computed(() => {
  return String(form.seedsText)
    .split(/[,\s]+/)
    .map(s => s.trim())
    .filter(Boolean)
    .map(Number)
    .filter(n => Number.isFinite(n))
})

const experimentsPreview = computed(() => {
  return seeds.value.map(seed => ({
    seed,
    solver_job: 'http',
    solver_route: 'http',
    fjsp_image: fjspImage(form.fjsp_algo),
    mapf_image: mapfImage(form.mapf_algo),
    mapf_obs_type: form.mapf_obs_type,
    ...(form.fjsp_instance ? { fjsp_instance: form.fjsp_instance } : {}),
    ...(form.mapf_instance ? { mapf_instance: form.mapf_instance } : {}),
  }))
})

const canStart = computed(() => !running.value && experimentsPreview.value.length > 0)

// ============ 运行状态 ============
const running = ref(false)
const status = reactive({
  idx: 0,
  total: 0,
  cancelled: false,
  done: false,
  error: '',
})
// logs 用 shallowRef：数组本身响应式，元素不被深代理（避免大数组 patch 慢）
// 每条日志预解析 isErr / epTag，模板里不再做字符串运算
const logs = shallowRef([])
const results = ref([])
const logBoxRef = ref(null)
const MAX_LOG_LINES = 5000

// 日志节流：高频 SSE 日志（每秒可能上百行）先入 buffer，定时批量 flush 到 logs
// 否则每行触发一次响应式 + DOM patch，第 2 个 episode logs 突破 2000 后会卡死浏览器
let _logBuffer = []
let _logIdCounter = 0
let _logFlushTimer = null
const LOG_FLUSH_INTERVAL = 100  // ms
const LOG_FLUSH_BATCH = 200     // 单次最多 flush 多少行（防极端 burst 一次性塞太多）

function _makeLogEntry(text) {
  const lower = text.toLowerCase()
  return {
    id: ++_logIdCounter,                              // 稳定 key，splice 不会引起整体重渲染
    text,                                             // 已含 "[ep#N] xxx" 前缀，不再单独抽 epTag
    isErr: lower.includes('error') || lower.includes('traceback'),  // 预计算，模板直接读
  }
}

function _flushLogs() {
  if (_logBuffer.length === 0) {
    _logFlushTimer = null  // 关键：buffer 空时清掉 timer id，下次 pushLog 才能重新调度
    return
  }
  const take = _logBuffer.splice(0, Math.min(_logBuffer.length, LOG_FLUSH_BATCH))
  const next = logs.value.concat(take)
  // 超容量时整体裁剪一次（构造新数组，避免 in-place splice 引起 key 大幅迁移）
  if (next.length > MAX_LOG_LINES) {
    next.splice(0, next.length - MAX_LOG_LINES)
  }
  logs.value = next  // shallowRef 一次性触发 patch
  nextTick(() => {
    if (logBoxRef.value) logBoxRef.value.scrollTop = logBoxRef.value.scrollHeight
  })
  // buffer 还有剩余 → 立即再排一帧；空了就置 null，否则后续 pushLog 不会调度新 timer
  if (_logBuffer.length > 0) {
    _logFlushTimer = setTimeout(_flushLogs, LOG_FLUSH_INTERVAL)
  } else {
    _logFlushTimer = null
  }
}

function pushLog(line) {
  _logBuffer.push(_makeLogEntry(line))
  if (_logFlushTimer == null) {
    _logFlushTimer = setTimeout(_flushLogs, LOG_FLUSH_INTERVAL)
  }
}

let evtSource = null

const progressPercent = computed(() => {
  if (!status.total) return 0
  return Math.round((status.idx / status.total) * 100)
})

// ============ 文件上传 ============
async function onUpload(e, kind) {
  const file = e.target.files?.[0]
  e.target.value = ''
  if (!file) return
  const fd = new FormData()
  fd.append('file', file)
  fd.append('kind', kind)
  try {
    const resp = await fetch(getApiUrl(API_ROUTES.BATCH_UPLOAD_INSTANCE), {
      method: 'POST',
      body: fd,
    })
    const data = await resp.json()
    if (data.status === 'ok') {
      if (kind === 'fjsp') form.fjsp_instance = data.filename
      else form.mapf_instance = data.filename
      ElMessage.success(`已上传：${data.filename} (${data.size}B)`)
    } else {
      ElMessage.error(data.message || '上传失败')
    }
  } catch (err) {
    ElMessage.error('上传请求失败: ' + err.message)
  }
}

// ============ 启动 / 取消 ============
async function start() {
  if (!canStart.value) return
  // 清空日志 buffer + 取消未触发的 flush 定时器
  if (_logFlushTimer != null) { clearTimeout(_logFlushTimer); _logFlushTimer = null }
  _logBuffer = []
  logs.value = []
  results.value = []
  status.idx = 0
  status.total = experimentsPreview.value.length
  status.cancelled = false
  status.done = false
  status.error = ''

  try {
    const resp = await apiPost(API_ROUTES.BATCH_START, {
      experiments: experimentsPreview.value,
    })
    if (resp.status !== 'started') {
      ElMessage.error(resp.message || '启动失败')
      return
    }
    running.value = true
    openStream()
    ElMessage.success(`批处理已启动：${resp.total} 个 episode`)
  } catch (err) {
    ElMessage.error('启动请求失败: ' + err.message)
  }
}

async function cancel() {
  try {
    await apiPost(API_ROUTES.BATCH_CANCEL, {})
    ElMessage.info('已发送取消')
  } catch (err) {
    ElMessage.error('取消失败: ' + err.message)
  }
}

function openStream() {
  closeStream()
  evtSource = new EventSource(getApiUrl(API_ROUTES.BATCH_STREAM))

  evtSource.addEventListener('batch_progress', (e) => {
    const d = JSON.parse(e.data)
    status.idx = d.idx
    status.total = d.total
    pushLog(`========== ep#${d.idx}/${d.total}  seed=${d.cfg?.seed}  ${d.cfg?.solver_job}/${d.cfg?.solver_route} ==========`)
  })

  evtSource.addEventListener('batch_log', (e) => {
    const d = JSON.parse(e.data)
    pushLog(`[ep#${d.idx}] ${d.line}`)
  })

  evtSource.addEventListener('batch_metric', (e) => {
    const d = JSON.parse(e.data)
    results.value.push({
      run_id: `run_${d.idx}`,
      cfg: d.cfg,
      metrics: d.metrics,
      terminated_reason: d.metrics?.terminated_reason,
    })
  })

  evtSource.addEventListener('batch_done', (e) => {
    const d = JSON.parse(e.data)
    status.cancelled = !!d.cancelled
    status.done = true
    running.value = false
    pushLog(`========== 批处理完成：${d.completed}/${d.total}${d.cancelled ? '（已取消）' : ''} ==========`)
    // 强制把残留 buffer 全部 flush 出来（防止最后一段日志卡在 buffer 里）
    if (_logFlushTimer != null) { clearTimeout(_logFlushTimer); _logFlushTimer = null }
    _flushLogs()
    closeStream()
  })

  evtSource.addEventListener('batch_error', (e) => {
    const d = JSON.parse(e.data)
    status.error = d.message
    running.value = false
    pushLog(`[ERROR] ${d.message}`)
    ElMessage.error('批处理异常：' + d.message)
    if (_logFlushTimer != null) { clearTimeout(_logFlushTimer); _logFlushTimer = null }
    _flushLogs()
    closeStream()
  })

  evtSource.onerror = () => {
    if (running.value) {
      apiGet(API_ROUTES.BATCH_STATUS).then(s => {
        if (s.error) {
          running.value = false
          status.done = true
          status.error = s.error
          ElMessage.error('批处理异常：' + s.error)
          closeStream()
        } else if (!s.running) {
          running.value = false
          status.done = true
          closeStream()
        }
      }).catch(() => {})
    }
  }
}

function closeStream() {
  if (evtSource) {
    evtSource.close()
    evtSource = null
  }
}

function fmt(v, percent = false) {
  if (v === '' || v === undefined || v === null) return '-'
  const n = Number(v)
  if (!Number.isFinite(n)) return String(v)
  if (percent) return (n * 100).toFixed(1) + '%'
  return Number.isInteger(n) ? String(n) : n.toFixed(3)
}

// 仅在批处理运行时阻止关闭面板卸载组件丢状态；
// 关闭面板时不取消容器（用户可能想后台跑），由后端自行管理生命周期
onBeforeUnmount(() => {
  closeStream()
  if (_logFlushTimer != null) { clearTimeout(_logFlushTimer); _logFlushTimer = null }
})
</script>

<style scoped>
.batch-panel {
  display: flex;
  flex-direction: column;
  height: 100%;
  overflow: hidden;
  font-family: 'Inter', system-ui, sans-serif;
  color: rgba(220, 230, 245, 0.95);
}

/* 与工厂视图一致的 plan-select 风格 */
.plan-select {
  width: 100%;
  padding: 7px 10px;
  border: 1px solid rgba(100, 180, 255, 0.15);
  background: rgba(20, 25, 45, 0.6);
  border-radius: 6px;
  cursor: pointer;
  color: rgba(200, 220, 255, 0.9);
  font-size: 12px;
  font-family: inherit;
  outline: none;
  transition: border-color 0.2s;
}
.plan-select option {
  background: #141929;
  color: rgba(200, 220, 255, 0.9);
}
.plan-select:hover:not(:disabled) {
  border-color: rgba(100, 180, 255, 0.35);
}
.plan-select:focus {
  border-color: rgba(100, 180, 255, 0.55);
}
.plan-select:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* body 布局 */
.batch-body {
  display: grid;
  grid-template-columns: 320px 1fr;
  gap: 14px;
  flex: 1;
  min-height: 0;
}

.panel {
  background: rgba(20, 25, 45, 0.5);
  border: 1px solid rgba(255,255,255,0.06);
  border-radius: 10px;
  padding: 12px 14px;
  display: flex;
  flex-direction: column;
  min-height: 0;
}
.form-panel {
  overflow-y: auto;
}
.run-panel {
  overflow: hidden;
}
.panel-title {
  font-size: 13px;
  font-weight: 600;
  color: rgba(200, 220, 255, 0.9);
  margin-bottom: 12px;
  display: flex; align-items: center; gap: 10px;
}
.panel-subtitle {
  font-size: 11px;
  color: rgba(100, 180, 255, 0.8);
  letter-spacing: 0.5px;
  text-transform: uppercase;
  margin: 12px 0 6px;
  display: flex; justify-content: space-between; align-items: center;
}

/* 表单 */
.form-row {
  display: flex; flex-direction: column;
  gap: 4px;
  margin-bottom: 8px;
}
.form-row label {
  font-size: 11px;
  color: rgba(160, 190, 230, 0.7);
}
/* input（种子输入框）—— 与 plan-select 视觉一致 */
.form-row input {
  width: 100%;
  background: rgba(20, 25, 45, 0.6);
  border: 1px solid rgba(100, 180, 255, 0.15);
  color: rgba(200, 220, 255, 0.9);
  padding: 7px 10px;
  border-radius: 6px;
  font-size: 12px;
  font-family: inherit;
  outline: none;
  transition: border-color 0.2s;
}
.form-row input:focus {
  border-color: rgba(100, 180, 255, 0.55);
}
.form-row input::placeholder {
  color: rgba(160, 190, 230, 0.4);
}
.hint {
  font-size: 10px;
  color: rgba(160, 190, 230, 0.5);
}

/* upload */
.upload-row {
  display: flex; align-items: center; gap: 8px;
  margin-bottom: 6px;
}
.upload-label {
  flex: 1;
  display: flex; flex-direction: column; gap: 2px;
  font-size: 11px;
  color: rgba(160, 190, 230, 0.7);
}
.upload-current {
  font-size: 10px;
  color: rgba(160, 190, 230, 0.4);
  font-family: 'JetBrains Mono', monospace;
  word-break: break-all;
}
.upload-current.set {
  color: rgba(102, 208, 106, 0.9);
}
.upload-btn {
  padding: 4px 9px;
  background: rgba(100, 180, 255, 0.1);
  border: 1px solid rgba(100, 180, 255, 0.3);
  border-radius: 4px;
  font-size: 11px;
  color: rgba(100, 180, 255, 0.9);
  cursor: pointer;
}
.upload-btn:hover { background: rgba(100, 180, 255, 0.18); }
.clear-btn {
  padding: 4px 8px;
  background: transparent;
  border: 1px solid rgba(255,255,255,0.1);
  border-radius: 4px;
  font-size: 10px;
  color: rgba(255, 180, 180, 0.7);
  cursor: pointer;
}

/* buttons */
.action-row {
  display: flex; gap: 6px;
  margin-top: 12px;
}
.primary-btn {
  flex: 1;
  padding: 8px 0;
  background: linear-gradient(135deg, rgba(102, 126, 234, 0.6), rgba(118, 75, 162, 0.6));
  border: 1px solid rgba(102, 126, 234, 0.4);
  border-radius: 6px;
  color: white;
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.15s;
}
.primary-btn:hover:not(:disabled) {
  background: linear-gradient(135deg, rgba(102, 126, 234, 0.8), rgba(118, 75, 162, 0.8));
}
.primary-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}
.danger-btn {
  padding: 8px 14px;
  background: rgba(255, 100, 100, 0.15);
  border: 1px solid rgba(255, 100, 100, 0.4);
  border-radius: 6px;
  color: rgba(255, 180, 180, 0.95);
  font-size: 12px;
  cursor: pointer;
}
.danger-btn:disabled { opacity: 0.3; cursor: not-allowed; }

/* status tag */
.status-tag {
  font-size: 10px;
  padding: 2px 8px;
  border-radius: 10px;
  font-weight: 500;
}
.status-tag.running {
  background: rgba(100, 180, 255, 0.15);
  color: #64b4ff;
  animation: pulse 1.5s infinite;
}
.status-tag.done {
  background: rgba(102, 208, 106, 0.15);
  color: #66d06a;
}
.status-tag.cancelled {
  background: rgba(255, 180, 80, 0.15);
  color: #ffb450;
}
.status-tag.idle {
  background: rgba(160, 190, 230, 0.1);
  color: rgba(160, 190, 230, 0.6);
}
@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}

/* progress */
.progress-bar {
  height: 5px;
  background: rgba(255,255,255,0.06);
  border-radius: 3px;
  overflow: hidden;
  margin-bottom: 6px;
}
.progress-fill {
  height: 100%;
  background: linear-gradient(90deg, rgba(100, 180, 255, 0.6), rgba(170, 100, 255, 0.7));
  transition: width 0.3s ease;
}

/* log */
.log-box {
  background: rgba(0, 0, 0, 0.35);
  border: 1px solid rgba(255,255,255,0.04);
  border-radius: 6px;
  padding: 8px;
  flex: 1;
  min-height: 120px;
  overflow-y: auto;
  font-family: 'JetBrains Mono', 'Menlo', monospace;
  font-size: 11px;
  line-height: 1.5;
}
.log-line {
  color: rgba(220, 230, 245, 0.85);
  white-space: pre-wrap;
  word-break: break-all;
}
.log-line.err { color: rgba(255, 130, 130, 0.9); }
.log-ep {
  color: rgba(170, 100, 255, 0.8);
  margin-right: 4px;
}
.log-empty {
  color: rgba(160, 190, 230, 0.4);
  font-style: italic;
  text-align: center;
  padding: 20px 0;
}

/* result table */
.result-table-wrap {
  background: rgba(0, 0, 0, 0.25);
  border: 1px solid rgba(255,255,255,0.04);
  border-radius: 6px;
  padding: 6px;
  max-height: 200px;
  overflow: auto;
}
.result-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 11px;
  font-variant-numeric: tabular-nums;
}
.result-table th {
  text-align: left;
  padding: 5px 8px;
  color: rgba(160, 190, 230, 0.7);
  border-bottom: 1px solid rgba(255,255,255,0.06);
  font-weight: 500;
  position: sticky;
  top: 0;
  background: rgba(20, 25, 45, 0.95);
}
.result-table td {
  padding: 4px 8px;
  border-bottom: 1px solid rgba(255,255,255,0.03);
  color: rgba(220, 230, 245, 0.85);
}
.result-table tr.err td {
  color: rgba(255, 130, 130, 0.7);
}
.result-table td.mono { font-family: 'JetBrains Mono', monospace; }
.result-table td.small { font-size: 10px; }
</style>
