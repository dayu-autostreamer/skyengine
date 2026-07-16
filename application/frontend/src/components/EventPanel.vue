<template>
    <div class="event-panel">
        <div class="event-header">
            <div class="header-left">
                <h3>{{ title }}</h3>
                <span class="event-counter" v-if="monitorStore.totalEventCount > 0">
                    Total: {{ monitorStore.totalEventCount }}
                </span>
            </div>
            <div class="header-actions">
                <button
                    class="icon-btn export-btn"
                    title="导出当前日志 (JSON)"
                    @click="handleExportLive"
                >⬇</button>
                <button
                    class="icon-btn analysis-btn"
                    title="查看历史样本"
                    @click="goToAnalysis"
                >📊</button>
                <button @click="monitorStore.clear" class="clear-btn icon-btn" title="清空">×</button>
            </div>
        </div>

        <!-- 嵌入：历史分析样本（默认展开，显示全部） -->
        <div v-if="analysisLog.totalRuns > 0" class="recent-runs-wrap">
            <div class="recent-runs-head" @click="toggleRecent">
                <span class="recent-title">
                    📦 历史样本
                    <span class="recent-count">{{ analysisLog.totalRuns }}</span>
                </span>
                <span class="recent-toggle">{{ showRecent ? '▾' : '▸' }}</span>
            </div>
            <transition name="recent-slide">
                <div v-show="showRecent" class="recent-runs-list">
                    <div
                        v-for="run in analysisLog.runs"
                        :key="run.id"
                        class="recent-run-item"
                        @click="openRun(run.id)"
                    >
                        <div class="recent-run-row">
                            <span class="recent-run-id">{{ run.id }}</span>
                            <span class="recent-run-factory">{{ run.factory_id }}</span>
                        </div>
                        <div class="recent-run-meta">
                            <span>{{ run.summary.total_steps }} 步</span>
                            <span>{{ run.summary.completed_jobs }}/{{ run.summary.total_jobs }} jobs</span>
                            <span>{{ run.summary.event_total }} events</span>
                        </div>
                    </div>
                </div>
            </transition>
        </div>

        <div class="event-list" ref="eventListRef">
            <div v-if="monitorStore.events.length === 0" class="no-events">
                <span>暂无系统日志</span>
            </div>

            <transition-group name="event-list-anim" tag="div" v-else>
                <div v-for="event in monitorStore.events" :key="event.id" class="event-item"
                    :class="['event-' + (event.level || 'info'), { expanded: expandedEventId === event.id }]"
                    @click="toggleEvent(event.id)">
                    <div class="event-meta">
                        <span class="event-time">{{ formatTime(event.timestamp) }}</span>
                        <span class="event-idx">#{{ event.idx }}</span>
                    </div>
                    <div class="event-content">
                        <span class="event-icon">{{ getEventIcon(event) }}</span>
                        <div class="event-text">
                            <div class="event-title-row">
                                <span v-if="event.title" class="event-title">{{ event.title }}</span>
                                <span v-if="event.category" class="event-category">{{ event.category }}</span>
                            </div>
                            <div v-if="event.message" class="event-message">{{ event.message }}</div>
                        </div>
                    </div>
                    <div v-if="expandedEventId === event.id" class="event-detail">
                        <div class="event-detail-row">
                            <span>type</span>
                            <code>{{ event.type || 'narrative' }}</code>
                        </div>
                        <div class="event-detail-row">
                            <span>step</span>
                            <code>{{ event.step ?? event.idx ?? '--' }}</code>
                        </div>
                        <div v-if="event.category" class="event-detail-row">
                            <span>category</span>
                            <code>{{ event.category }}</code>
                        </div>
                        <pre v-if="hasPayload(event)" class="event-payload">{{ formatPayload(event.payload) }}</pre>
                        <div v-else class="event-payload empty">无附加 payload</div>
                    </div>
                </div>
            </transition-group>
        </div>
    </div>
</template>

<script setup>
import { ref, watch, nextTick } from 'vue'
import { useMonitorStore } from '@/stores/monitor'
import { useAnalysisLogStore } from '@/stores/analysisLog'
import { useFactoryStore } from '@/stores/factory'
import { ElMessage } from 'element-plus'

defineProps({
    title: { type: String, default: '📋 系统事件' }
})

const monitorStore = useMonitorStore()
const analysisLog = useAnalysisLogStore()
const factoryStore = useFactoryStore()
const eventListRef = ref(null)
const expandedEventId = ref(null)
// 默认展开历史样本列表；用户手动收起后保持收起
const showRecent = ref(true)

function toggleRecent() {
    showRecent.value = !showRecent.value
}

function goToAnalysis() {
    // 不再走路由（避免卸载 FactoryView 打断执行流），改为打开工厂内浮层
    analysisLog.openPanel()
}

function openRun(id) {
    analysisLog.openPanel(id)
}

function toggleEvent(id) {
    expandedEventId.value = expandedEventId.value === id ? null : id
}

function hasPayload(event) {
    return event?.payload && typeof event.payload === 'object' && Object.keys(event.payload).length > 0
}

function formatPayload(payload) {
    try {
        return JSON.stringify(payload || {}, null, 2)
    } catch {
        return String(payload)
    }
}

// 导出当前会话日志（不入库，直接序列化当前 store 数据）
async function handleExportLive() {
    try {
        await analysisLog.exportLive(factoryStore, monitorStore, {
            factory_id: factoryStore.selectedFactoryId,
        })
        ElMessage.success('已导出当前日志')
    } catch (e) {
        console.error('[EventPanel] exportLive failed:', e)
        ElMessage.error('导出失败')
    }
}

// 工具函数：canonical event {type(业务), level, message}
// 图标优先按已知业务 type 精修，其次按 level 兜底
const eventIconMap = {
    // level 兜底
    info: 'ℹ️', success: '✅', warning: '⚠️', error: '❌',
    // 已知业务 type 专属图标
    sim_started: '🚀', episode_completed: '🏁', episode_truncated: '⏹️',
    narrative: '📌',
    machine_start_op: '⚙️', machine_idle: '💤',
    transfer_started: '🚛', transfer_completed: '📦',
    transfer_destination_resolved: '📍',
    job_completed: '🎯', job_released: '📤',
    agv_assigned: '🤖', agv_freed: '🟢',
    machine_breakdown: '🛑', machine_recovery: '🔧',
    agv_breakdown: '🚨', agv_recovery: '🟢',
    temporary_obstacle: '⛔', obstacle_clear: '🧹',
    urgent_job_arrival: '⚡',
    job_replan_started: '↻', job_replan_completed: '✓', job_replan_failed: '✕',
    job_insertion_phase_changed: '▸',
    job_preempted: 'Ⅱ', job_resumed: '▶',
}
function getEventIcon(ev) {
    if (!ev) return 'ℹ️'
    return eventIconMap[ev.type] || eventIconMap[ev.level] || 'ℹ️'
}
function formatTime(ts) {
    if (ts == null) return ''
    // canonical 是 "T+xs" 字符串，直接展示；Date 对象走 toLocaleTimeString
    if (typeof ts === 'string') return ts
    return new Date(ts).toLocaleTimeString('zh-CN', { hour12: false })
}

// 监听 Store 变化实现自动滚动
watch(
    () => monitorStore.events.length,
    () => {
        nextTick(() => {
            if (eventListRef.value) {
                eventListRef.value.scrollTo({
                    top: eventListRef.value.scrollHeight,
                    behavior: 'smooth'
                })
            }
        })
    }
)
</script>
<style scoped>
@import './styles/EventPanel.css';
</style>
