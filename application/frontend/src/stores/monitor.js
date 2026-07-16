import { defineStore } from 'pinia'
import { ref } from 'vue'

export const useMonitorStore = defineStore('monitor', () => {
    // ============ 1. 事件队列 (Event Queue) ============
    const eventQueue = ref([])
    const totalEventCount = ref(0)
    const eventKeySet = new Set()

    // ============ 2. 图表/指标 State ============
    const chartData = ref({
        machine: { labels: [], data: [] },
        agv: { labels: [], data: [] },
        job: { labels: [], data: [] }
    })

    const keyMetrics = ref({
        efficiency: { value: '--', type: 'info' },
        utilization: { value: '--', type: 'info' }
    })

    // ============ 3. 运行时数据累积 (RAG 上下文) ============
    const metricsTimeline = ref([])
    const MAX_METRICS_TIMELINE = 500

    const runId = ref(null)
    const runStartTime = ref(null)
    const runMeta = ref({})

    // ============ 4. sim_server (DockerFactory) 专用 ============
    // episode 结束后的汇总 + 热力图
    const heatmaps = ref(null)
    const episodeSummary = ref(null)

    // ============ 5. 智能体对话历史 (跨组件持久) ============
    // 结构: { id, role: 'user'|'assistant', content, timestamp, templateId?, streaming?, error? }
    const agentHistory = ref([])
    const MAX_AGENT_HISTORY = 30
    // 最近选中的模板 id (用于按钮高亮持久)
    const agentActiveTemplate = ref(null)

    /** 追加一条 Agent 消息 */
    function pushAgentMessage(msg) {
        agentHistory.value.push({
            id: Date.now() + Math.random(),
            timestamp: new Date(),
            ...msg,
        })
        if (agentHistory.value.length > MAX_AGENT_HISTORY) {
            agentHistory.value = agentHistory.value.slice(-MAX_AGENT_HISTORY)
        }
    }

    /** 流式追加 chunk 到最后一条 assistant(没有则新建) */
    function appendAgentChunk(chunk) {
        const last = agentHistory.value[agentHistory.value.length - 1]
        if (last && last.role === 'assistant' && last.streaming) {
            last.content += chunk
        } else {
            pushAgentMessage({ role: 'assistant', content: chunk, streaming: true })
        }
    }

    /** 结束最后一条消息流式状态 */
    function finalizeAgentMessage() {
        const last = agentHistory.value[agentHistory.value.length - 1]
        if (last) last.streaming = false
    }

    /** 标记最后一条 assistant 失败 */
    function failAgentMessage(errMsg) {
        const last = agentHistory.value[agentHistory.value.length - 1]
        if (last && last.role === 'assistant') {
            last.streaming = false
            last.error = true
            if (!last.content) last.content = errMsg || '⚠ AI 服务暂不可用'
        }
    }

    /** 清空 Agent 对话历史 */
    function clearAgentHistory() {
        agentHistory.value = []
        agentActiveTemplate.value = null
    }

    // ============ 动作 (Actions) ============

    /**
     * 推送事件入队 (Push) — canonical shape
     * payload: { type(业务名), level(info|success|warning|error), message, idx, timestamp, category, title, payload, step }
     *
     * 内部存储形如：
     *   { id, timestamp, idx, type, level, message }
     * 其中 timestamp 优先用 payload 传入的 "T+xs" canonical 字符串；
     * 未提供时退化为 Date 对象（兼容老调用）。
     */
    function eventKey(payload) {
        const type = payload?.type || 'narrative'
        const step = payload?.step ?? payload?.idx ?? 0
        const category = payload?.category || ''
        const eventPayload = payload?.payload || {}
        return `${step}|${category}|${type}|${JSON.stringify(eventPayload)}`
    }

    function pushEvent(payload, { dedupe = false } = {}) {
        const key = eventKey(payload)
        if (dedupe && eventKeySet.has(key)) {
            return
        }
        const {
            type = 'narrative',
            level = 'info',
            message = '',
            idx = 0,
            timestamp = null,
            category = null,
            title = '',
            payload: eventPayload = {},
            step = idx,
        } = payload

        const newEvent = {
            id: Date.now() + Math.random(),
            timestamp: timestamp != null ? timestamp : new Date(),
            idx,
            step,
            category,
            type, // 业务名：machine_start_op / transfer_started / narrative / ...
            level, // info / success / warning / error
            title,
            message,
            payload: eventPayload,
        }

        eventQueue.value.push(newEvent)
        eventKeySet.add(key)
        totalEventCount.value++
    }

    /**
     * 推送指标更新 (Push) — canonical shape
     * data: { status, step, metrics:{...}, metrics_reward }
     *
     * 同时累积到 metricsTimeline（canonical 形态，与 pushSimMetrics 同构），
     * 并从 metrics 字段 dual-write 派生 chartData / keyMetrics，让旧 MetricsPanel
     * 继续工作（不破坏 RightSidePanel / FactoryTabsPanel）。
     */
    function pushMetrics(data) {
        if (!data || !data.metrics) return

        // 1) 累积 canonical timeline
        metricsTimeline.value.push({
            step: data.step,
            timestamp: Date.now(),
            metrics: { ...data.metrics },
            metrics_reward: data.metrics_reward ?? 0,
        })
        if (metricsTimeline.value.length > MAX_METRICS_TIMELINE) {
            metricsTimeline.value = metricsTimeline.value.slice(-MAX_METRICS_TIMELINE)
        }

        // 2) 从 canonical metrics 派生旧 chartData / keyMetrics（兼容老 MetricsPanel）
        const m = data.metrics
        const utilPct = Math.round((m.machine_utilization ?? 0) * 100)
        const effPct = Math.round(((m.efficiency ?? m.agv_loaded_utilization ?? 0)) * 100)

        keyMetrics.value = {
            ...keyMetrics.value,
            efficiency: {
                value: `${effPct}%`,
                type: effPct >= 80 ? 'success' : effPct > 0 ? 'info' : 'danger',
            },
            utilization: {
                value: `${utilPct}%`,
                type: utilPct > 80 ? 'warning' : 'success',
            },
        }

        // chartData 派生：把 metrics 里的标量塞进 data 数组（labels 占位）
        // 注：旧 MetricsPanel 直接展示这些数组，保留语义合理即可
        chartData.value = {
            machine: {
                labels: ['M1', 'M2', 'M3'],
                data: [
                    Math.round((m.machine_utilization ?? 0) * 100),
                    Math.round((m.machine_non_processing_time_mean ?? 0) * 100),
                    Math.round((m.operation_queue_waiting_time_mean ?? 0) * 100),
                ],
            },
            agv: {
                labels: ['loaded', 'busy', 'travel', 'wait'],
                data: [
                    Math.round((m.agv_loaded_utilization ?? 0) * 100),
                    Math.round((m.agv_busy_utilization ?? 0) * 100),
                    m.agv_travel_time_total ?? 0,
                    m.agv_waiting_time_total ?? 0,
                ],
            },
            job: {
                labels: ['queue_wait', 'load_var', 'swap'],
                data: [
                    Math.round((m.operation_queue_waiting_time_mean ?? 0) * 100),
                    Math.round(m.machine_load_variance ?? 0),
                    m.swap_conflict_count ?? 0,
                ],
            },
        }
    }

    /**
     * 开始新运行
     */
    function startRun(meta = {}) {
        runId.value = meta.runId || `run_${Date.now()}`
        runStartTime.value = new Date().toISOString()
        runMeta.value = meta
        metricsTimeline.value = []
    }

    /**
     * 构造 RAG 上下文 — 从已有数据生成
     */
    function buildRAGContext(currentState = null) {
        const recentMetrics = metricsTimeline.value.slice(-20)

        // metrics 统计（读 canonical metrics 子字段）
        const metricStats = {}
        if (recentMetrics.length > 0) {
            const numOrNone = (v) => (typeof v === 'number' ? v : null)
            const effs = recentMetrics
                .map((m) => numOrNone(m.metrics?.efficiency ?? m.metrics?.agv_loaded_utilization))
                .filter((v) => v != null)
            const utils = recentMetrics
                .map((m) => numOrNone(m.metrics?.machine_utilization))
                .filter((v) => v != null)
            if (effs.length > 0) {
                const pctEffs = effs.map((v) => v * 100)
                metricStats.efficiency = {
                    current: pctEffs[pctEffs.length - 1],
                    avg: +(pctEffs.reduce((a, b) => a + b, 0) / pctEffs.length).toFixed(2),
                    min: Math.min(...pctEffs),
                    max: Math.max(...pctEffs),
                }
            }
            if (utils.length > 0) {
                const pctUtils = utils.map((v) => v * 100)
                metricStats.utilization = {
                    current: pctUtils[pctUtils.length - 1],
                    avg: +(pctUtils.reduce((a, b) => a + b, 0) / pctUtils.length).toFixed(2),
                    min: Math.min(...pctUtils),
                    max: Math.max(...pctUtils),
                }
            }
        }

        // 事件统计（按业务 type 计数）
        const eventStats = {}
        eventQueue.value.forEach(e => {
            eventStats[e.type] = (eventStats[e.type] || 0) + 1
        })

        return {
            run: {
                id: runId.value,
                start_time: runStartTime.value,
                meta: runMeta.value,
                duration: runStartTime.value
                    ? `${((Date.now() - new Date(runStartTime.value).getTime()) / 1000).toFixed(0)}s`
                    : '0s',
            },
            metric_stats: metricStats,
            event_stats: eventStats,
            total_events: totalEventCount.value,
            recent_metrics: recentMetrics.slice(-10),
            recent_events: eventQueue.value.slice(-20),
            current_state: currentState,
        }
    }

    // 重置/清空 Monitor 状态
    function clear() {
        eventQueue.value = []
        eventKeySet.clear()
        totalEventCount.value = 0
        metricsTimeline.value = []
        runId.value = null
        runStartTime.value = null
        runMeta.value = {}
        heatmaps.value = null
        episodeSummary.value = null
    }

    /**
     * 清空 sim_server 专用状态 (DockerFactory 切换场景时调用)
     */
    function clearSim() {
        eventQueue.value = []
        eventKeySet.clear()
        totalEventCount.value = 0
        metricsTimeline.value = []
        heatmaps.value = null
        episodeSummary.value = null
    }

    function loadArchiveData(metrics = [], events = []) {
        metricsTimeline.value = JSON.parse(JSON.stringify(metrics || []))
        eventKeySet.clear()
        eventQueue.value = JSON.parse(JSON.stringify(events || [])).map((event, idx) => ({
            id: event.id ?? Date.now() + idx + Math.random(),
            timestamp: event.timestamp ?? null,
            idx: event.idx ?? event.step ?? idx,
            step: event.step ?? event.idx ?? idx,
            category: event.category ?? null,
            type: event.type ?? 'narrative',
            level: event.level ?? 'info',
            title: event.title ?? '',
            message: event.message ?? '',
            payload: event.payload ?? {},
        }))
        eventQueue.value.forEach((event) => eventKeySet.add(eventKey(event)))
        totalEventCount.value = eventQueue.value.length
        heatmaps.value = null
        episodeSummary.value = null
    }

    /**
     * 推送 sim_server (DockerFactory) 指标更新
     * - data.status === "running": 增量时序点 {step, metrics:{...}, metrics_reward}
     * - data.status === "stopped": episode 汇总 + 热力图
     */
    function pushSimMetrics(data) {
        if (!data) return
        if (data.status === 'stopped') {
            if (data.episode_summary) episodeSummary.value = data.episode_summary
            if (data.heatmap) heatmaps.value = data.heatmap
            pushEvent({
                title: '仿真完成',
                message: `makespan=${data.episode_summary?.completed_makespan ?? '--'}`,
                type: 'success',
                idx: data.step ?? 0,
            }, { dedupe: true })
            return
        }
        if (data.status === 'running' && data.metrics) {
            metricsTimeline.value.push({
                step: data.step,
                timestamp: Date.now(),
                metrics: { ...data.metrics },
                metrics_reward: data.metrics_reward,
            })
            if (metricsTimeline.value.length > MAX_METRICS_TIMELINE) {
                metricsTimeline.value = metricsTimeline.value.slice(-MAX_METRICS_TIMELINE)
            }
        }
    }

    /**
     * 推送 sim_server (DockerFactory) 业务事件
     * data: {step, timestamp, category, type, title, message, level, payload} — 已是 canonical，直接委托 pushEvent
     */
    function pushSimEvent(data) {
        if (!data) return
        pushEvent({
            type: data.type || 'narrative',
            level: data.level || 'info',
            category: data.category || null,
            title: data.title || '',
            message: data.message || '',
            idx: data.step ?? 0,
            step: data.step ?? 0,
            timestamp: data.timestamp,
            payload: data.payload || {},
        }, { dedupe: true })
    }

    function exceptionTitle(type, payload = {}) {
        if (type === 'machine_breakdown') return '机器故障'
        if (type === 'machine_recovery') return '机器恢复'
        if (type === 'agv_breakdown') return 'AGV 故障'
        if (type === 'agv_recovery') return 'AGV 恢复'
        if (type === 'temporary_obstacle') return '临时障碍'
        if (type === 'obstacle_clear') return '障碍清除'
        if (type === 'urgent_job_arrival') return '紧急插单'
        return payload?.title || type || 'Exception'
    }

    function pushSimFrameEvents(events = [], fallbackStep = 0) {
        if (!Array.isArray(events) || events.length === 0) return
        events.forEach((event) => {
            const type = event?.type || 'exception'
            const step = event?.step ?? fallbackStep ?? 0
            pushEvent({
                type,
                level: event?.level || 'warning',
                category: event?.category || 'exception',
                title: event?.title || exceptionTitle(type, event?.payload),
                message: event?.message || '',
                idx: step,
                step,
                timestamp: event?.timestamp ?? `T+${step}s`,
                payload: event?.payload || {},
            }, { dedupe: true })
        })
    }

    return {
        // State
        events: eventQueue,
        totalEventCount,
        chartData,
        keyMetrics,
        // 新增 State
        metricsTimeline,
        runId,
        runStartTime,
        runMeta,
        // sim_server 专用
        heatmaps,
        episodeSummary,
        // Agent 对话
        agentHistory,
        agentActiveTemplate,

        // Actions
        pushEvent,
        pushMetrics,
        startRun,
        buildRAGContext,
        clear,
        // sim_server 专用
        clearSim,
        loadArchiveData,
        pushSimMetrics,
        pushSimEvent,
        pushSimFrameEvents,
        // Agent 对话
        pushAgentMessage,
        appendAgentChunk,
        finalizeAgentMessage,
        failAgentMessage,
        clearAgentHistory,
    }
})
