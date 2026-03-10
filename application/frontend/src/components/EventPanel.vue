<template>
    <div class="event-panel">
        <div class="event-header">
            <div class="header-left">
                <h3>{{ title }}</h3>
                <span class="event-counter" v-if="monitorStore.totalEventCount > 0">
                    Total: {{ monitorStore.totalEventCount }}
                </span>
            </div>
            <button @click="monitorStore.clearEvents" class="clear-btn" title="清空">×</button>
        </div>

        <div class="event-list" ref="eventListRef">
            <div v-if="monitorStore.events.length === 0" class="no-events">
                <span>暂无系统日志</span>
            </div>

            <transition-group name="event-list-anim" tag="div" v-else>
                <div v-for="event in monitorStore.events" :key="event.id" class="event-item"
                    :class="['event-' + event.type]">
                    <div class="event-meta">
                        <span class="event-time">{{ formatTime(event.timestamp) }}</span>
                        <span class="event-idx">#{{ event.idx }}</span>
                    </div>
                    <div class="event-content">
                        <span class="event-icon">{{ getEventIcon(event.type) }}</span>
                        <div class="event-text">
                            <div class="event-title">{{ event.title }}</div>
                            <div v-if="event.message" class="event-message">{{ event.message }}</div>
                        </div>
                    </div>
                </div>
            </transition-group>
        </div>
    </div>
</template>

<script setup>
import { ref, watch, nextTick } from 'vue'
import { useMonitorStore } from '@/stores/monitor' // 引入新 Store

defineProps({
    title: { type: String, default: '📋 系统事件' }
})

const monitorStore = useMonitorStore()
const eventListRef = ref(null)

// 工具函数保持不变...
const eventTypeMap = { success: '✅', warning: '⚠️', error: '❌', info: 'ℹ️', task: '📌', agv: '🚛', machine: '⚙️' }
function getEventIcon(type) { return eventTypeMap[type] || 'ℹ️' }
function formatTime(ts) { return new Date(ts).toLocaleTimeString('zh-CN', { hour12: false }) }

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