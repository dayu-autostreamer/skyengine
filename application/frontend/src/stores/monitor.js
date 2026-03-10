import { defineStore } from 'pinia'
import { ref } from 'vue'

export const useMonitorStore = defineStore('monitor', () => {
    // ============ 1. 事件队列 (Event Queue) ============
    // 【修复】统一变量名为 eventQueue，而不是 events
    const eventQueue = ref([])
    const totalEventCount = ref(0)
    
    // 【修复】统一常量名为 MAX_EVENT_BUFFER
    const MAX_EVENT_BUFFER = 50 

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

    // ============ 动作 (Actions) ============

    /**
     * 推送事件入队 (Push)
     */
    function pushEvent(payload) {
        const { title, message = '', type = 'info', idx = 0 } = payload

        const newEvent = {
            id: Date.now() + Math.random(),
            timestamp: new Date(),
            idx,
            title,
            message,
            type
        }

        // 【修复】使用正确的变量名 eventQueue
        eventQueue.value.push(newEvent)
        totalEventCount.value++

        // 维护队列长度 (FIFO)
        if (eventQueue.value.length > MAX_EVENT_BUFFER) {
            eventQueue.value.shift()
        }
    }

    /**
     * 推送指标更新 (Push)
     */
    function pushMetrics(data) {
        // 更新图表
        if (data.machine) chartData.value.machine = data.machine
        if (data.agv) chartData.value.agv = data.agv
        if (data.job) chartData.value.job = data.job

        // 更新卡片指标
        if (data.keyMetrics) {
            keyMetrics.value = { ...keyMetrics.value, ...data.keyMetrics }
        }
    }

    // 【优化】重置/清空 Monitor 状态
    function clear() {
        eventQueue.value = []
        // chartData 也可以选择重置，看需求
        // totalEventCount.value = 0 // 通常不清空历史总数
    }

    return {
        // State
        events: eventQueue, // 【关键】为了兼容组件中的 v-for="event in monitorStore.events"，这里别名导出
        totalEventCount,
        chartData,
        keyMetrics,

        // Actions
        pushEvent,
        pushMetrics,
        clear
    }
})