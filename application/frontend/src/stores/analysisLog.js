/**
 * Analysis Log Store — 离线日志分析（0701 后端持久化版）
 *
 * 角色转变（0701）：
 *   之前：runs[] 是内存数据源，finalize 直接 unshift
 *   之后：runs[] 是 dataset/run/ 的内存镜像，所有写入走后端 API
 *
 * 公开接口：
 *   - runs / totalRuns / panelOpen / initialRunId / loading
 *   - openPanel(runId?) / closePanel()
 *   - async listRuns()                     → GET /analysis/runs（轻列表）
 *   - async loadRun(id)                    → GET /analysis/runs/{id}（重详情）
 *   - async finalizeFromStores(fs, ms, meta)  → POST /analysis/runs
 *   - async importRun(payload, filename)   → POST /analysis/runs?source=imported
 *   - async deleteRun(id)                  → DELETE /analysis/runs/{id}
 *   - async exportRun(id)                  → 通过浏览器下载 GET /analysis/runs/{id}
 *   - getRunById(id) / computeSummary(...)
 *
 * Run schema 详见 docs/explore/0701日志详细设计.md §2
 */
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { apiGet, apiPost, apiDelete, API_ROUTES } from '@/utils/api'
import { STATIC_FACTORY_CONFIG } from '@/scenarios/fullSystemTest'

const SCHEMA_VERSION = '1.1'

export function collectInsertionRequests(frames, explicit = []) {
  const records = new Map()
  for (const record of explicit || []) {
    if (record?.request_id) records.set(record.request_id, record)
  }
  for (const frame of frames || []) {
    for (const record of frame?.insertion_requests || []) {
      if (record?.request_id) records.set(record.request_id, record)
    }
  }
  return [...records.values()].sort((a, b) =>
    Number(a.accepted_step ?? 0) - Number(b.accepted_step ?? 0),
  )
}

/**
 * 派生 summary（永远重算，外部 JSON 自带的 summary 字段一律忽略）。
 * 与后端 service.compute_summary 同形。
 */
export function computeSummary(frames, metricsTimeline, events) {
  frames = frames || []
  metricsTimeline = metricsTimeline || []
  events = events || []

  const lastFrame = frames[frames.length - 1] || {}
  const jobs = lastFrame.jobs || []
  const completedJobs = jobs.filter((j) => j && j.is_completed).length
  const totalJobs = jobs.length

  const utils = metricsTimeline
    .map((p) => p?.metrics?.machine_utilization)
    .filter((v) => typeof v === 'number')
  const avgUtilization = utils.length > 0 ? utils.reduce((a, b) => a + b, 0) / utils.length : null

  const eventCounts = events.reduce((acc, e) => {
    const t = e?.type || 'unknown'
    acc[t] = (acc[t] || 0) + 1
    return acc
  }, {})
  const insertionRequests = collectInsertionRequests(frames)

  return {
    total_steps: frames.length,
    completed_jobs: completedJobs,
    total_jobs: totalJobs,
    avg_utilization: avgUtilization,
    event_total: events.length,
    event_counts: eventCounts,
    insertion_count: insertionRequests.length,
    insertion_completed: insertionRequests.filter((record) => record.phase === 'completed').length,
    insertion_failed: insertionRequests.filter((record) => record.phase === 'failed').length,
  }
}

/**
 * 构造 config_snapshot。
 * - StaticFactory：直接复用 STATIC_FACTORY_CONFIG（剧本常量 + job_spec 投影）
 * - 容器化通路：从首帧 machines + jobs 投影（暂用兜底，未来 engine 提供再切）
 */
function buildConfigSnapshot(frames, factoryId) {
  if (factoryId === 'static_factory' || factoryId === 'northeast_center') {
    return JSON.parse(JSON.stringify(STATIC_FACTORY_CONFIG))
  }
  // 容器化通路兜底：从首帧投影
  const firstFrame = frames?.[0] || {}
  const machines = (firstFrame.machines || [])
    .map((m) => ({ id: String(m.id), location: m.location || null }))
  const jobs = (firstFrame.jobs || []).map((j) => ({
    job_id: j.job_id,
    release: j.release,
    due: j.due,
    ops: (j.ops || []).map((o) => ({
      op_id: o.op_id,
      proc_time: o.proc_time,
      assigned_machine: o.assigned_machine,
    })),
  }))
  return {
    factory_layout: { machines, agv_count: firstFrame.grid_state?.positions_xy?.length || 0 },
    job_spec: jobs,
    algorithm_params: null,
  }
}

/**
 * factory_id 规范化：alias 收敛（详见 0701日志详细设计.md §1.2）
 */
function canonicalFactoryId(raw) {
  if (!raw) return 'unknown'
  if (raw === 'northeast_center') return 'static_factory'
  return raw
}

export const useAnalysisLogStore = defineStore('analysisLog', () => {
  // —— 镜像状态 ——
  const runs = ref([])              // 轻量元信息列表（不含三流）
  const currentDetail = ref(null)   // 当前详情 Run（按需加载，含三流）
  const loading = ref(false)
  const detailLoading = ref(false)
  const error = ref(null)

  // —— 浮层 UI ——
  const panelOpen = ref(false)
  const initialRunId = ref(null)

  const totalRuns = computed(() => runs.value.length)

  function openPanel(runId = null) {
    initialRunId.value = runId
    panelOpen.value = true
    // 打开即刷新列表
    listRuns().catch((e) => console.warn('[analysisLog] listRuns on open failed:', e))
  }

  function closePanel() {
    panelOpen.value = false
    initialRunId.value = null
    currentDetail.value = null
  }

  // ============ 后端交互 ============

  /** 拉取列表（轻）。失败设置 error，不抛。 */
  async function listRuns() {
    loading.value = true
    error.value = null
    try {
      const resp = await apiGet(API_ROUTES.ANALYSIS_RUNS, { timeout: 15000 })
      runs.value = resp?.runs || []
    } catch (e) {
      error.value = e.message || String(e)
      console.warn('[analysisLog] listRuns failed:', e)
      runs.value = []
    } finally {
      loading.value = false
    }
  }

  /** 加载详情（重，含三流）。返回 Run 或 null。失败时把错误写入 error。 */
  async function loadRun(id) {
    detailLoading.value = true
    error.value = null
    try {
      const resp = await apiGet(
        API_ROUTES.ANALYSIS_RUN_DETAIL,
        { params: { run_id: id }, timeout: 15000 },
      )
      const run = resp?.run || null
      currentDetail.value = run
      if (!run) error.value = '后端返回空数据'
      return run
    } catch (e) {
      const status = e?.status
      if (status === 404) error.value = `样本不存在（404）：${id}`
      else error.value = `网络错误 (${status || e.message || e})`
      console.warn('[analysisLog] loadRun failed:', e)
      currentDetail.value = null
      return null
    } finally {
      detailLoading.value = false
    }
  }

  /** episode 结束：深拷贝三流 + 构造 config_snapshot + POST 落盘。返回 run（含后端 id）。 */
  async function finalizeFromStores(factoryStore, monitorStore, meta = {}) {
    const frames = JSON.parse(JSON.stringify(factoryStore.historyBuffer || []))
    const metricsTimeline = JSON.parse(JSON.stringify(monitorStore.metricsTimeline || []))
    const events = JSON.parse(JSON.stringify(monitorStore.eventQueue || monitorStore.events || []))
    const insertionRequests = collectInsertionRequests(frames)

    const factoryId = canonicalFactoryId(
      meta.factory_id || factoryStore.selectedFactoryId || 'unknown',
    )
    const algorithm = meta.algorithm || null

    const startedAt = frames[0]?.env_timeline || frames[0]?.timestamp || null
    const finishedAt =
      frames[frames.length - 1]?.env_timeline || frames[frames.length - 1]?.timestamp || null

    const payload = {
      schema_version: SCHEMA_VERSION,
      source: 'archive',
      original_filename: null,
      factory_id: factoryId,
      algorithm,
      created_at: new Date().toISOString(),
      started_at: startedAt,
      finished_at: finishedAt,
      total_steps: frames.length,
      config_snapshot: buildConfigSnapshot(frames, factoryId),
      frames,
      metricsTimeline,
      events,
      insertionRequests,
      summary: computeSummary(frames, metricsTimeline, events),
    }

    const resp = await apiPost(API_ROUTES.ANALYSIS_RUNS, payload, { timeout: 30000 })
    const savedRun = { ...payload, id: resp.id, filename: resp.filename }
    // 落盘成功后刷新列表镜像
    await listRuns()
    return savedRun
  }

  /** 用户上传 JSON 导入。校验三流 → POST source=imported → 刷新列表。返回 run。 */
  async function importRun(payload, originalFilename) {
    if (!payload || typeof payload !== 'object') {
      throw new Error('JSON 内容不是对象')
    }
    if (!Array.isArray(payload.frames) || !Array.isArray(payload.metricsTimeline) || !Array.isArray(payload.events)) {
      throw new Error('缺少必要字段：frames / metricsTimeline / events 必须为数组')
    }

    const body = {
      schema_version: SCHEMA_VERSION,
      source: 'imported',
      original_filename: originalFilename || null,
      factory_id: canonicalFactoryId(payload.factory_id),
      algorithm: payload.algorithm || null,
      created_at: payload.created_at || new Date().toISOString(),
      started_at: payload.started_at || null,
      finished_at: payload.finished_at || null,
      total_steps: payload.frames.length,
      config_snapshot: payload.config_snapshot || buildConfigSnapshot(payload.frames, payload.factory_id),
      frames: payload.frames,
      metricsTimeline: payload.metricsTimeline,
      events: payload.events,
      insertionRequests: collectInsertionRequests(payload.frames, payload.insertionRequests),
      // summary 由后端重算（C13：永远派生）
    }

    const resp = await apiPost(
      API_ROUTES.ANALYSIS_RUNS + '?source=imported',
      body,
      { timeout: 30000 },
    )
    await listRuns()
    return { ...body, id: resp.id, filename: resp.filename }
  }

  /** 删除。成功后从镜像移除。 */
  async function deleteRun(id) {
    await apiDelete(
      API_ROUTES.ANALYSIS_RUN_DETAIL,
      { params: { run_id: id }, timeout: 10000 },
    )
    runs.value = runs.value.filter((r) => r.id !== id)
    if (currentDetail.value?.id === id) currentDetail.value = null
  }

  /**
   * 通过浏览器下载已存档 Run。
   * 走 GET /analysis/runs/{id} 拿 JSON，前端 Blob 触发下载
   * （后端 GET 返回 JSON inline，浏览器侧用 a.download 即可）。
   */
  async function exportRun(id) {
    const run = await loadRun(id)
    if (!run) return false
    const blob = new Blob([JSON.stringify(run, null, 2)], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `${id}.json`
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    setTimeout(() => URL.revokeObjectURL(url), 1000)
    return true
  }

  function getRunById(id) {
    return runs.value.find((r) => r.id === id) || null
  }

  /**
   * 导出当前会话（EventPanel / DashboardPanel 调用）。
   * 0701 修订：新架构下"导出"= finalize 落盘 + 触发浏览器下载。
   * 行为上等同于 finalizeFromStores + exportRun，但保留旧 API 形态供调用方零改动。
   */
  async function exportLive(factoryStore, monitorStore, meta = {}) {
    const saved = await finalizeFromStores(factoryStore, monitorStore, meta)
    await exportRun(saved.id)
    return saved
  }

  return {
    // 镜像
    runs,
    currentDetail,
    loading,
    detailLoading,
    error,
    totalRuns,
    // UI
    panelOpen,
    initialRunId,
    openPanel,
    closePanel,
    // 后端交互
    listRuns,
    loadRun,
    finalizeFromStores,
    importRun,
    deleteRun,
    exportRun,
    exportLive,
    // 派生
    getRunById,
    computeSummary,
  }
})
