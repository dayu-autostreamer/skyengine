<template>
    <div class="metrics-panel">
        <div class="panel-header">
            <h3>📊 {{ title }}</h3>
        </div>

        <div class="metrics-grid">
            <div v-for="metric in metricsArray" :key="metric.label" class="metric-card"
                :class="metric.type || 'default'">
                <div class="metric-icon">{{ metric.icon }}</div>
                <div class="metric-content">
                    <div class="metric-label">{{ metric.label }}</div>
                    <div class="metric-value">{{ metric.value }}</div>
                    <div v-if="metric.detail" class="metric-detail">{{ metric.detail }}</div>
                </div>
            </div>
        </div>

        <div class="chart-section" v-if="showChart">
            <h4>实时监控图表</h4>
            <div class="chart-list">

                <div class="chart-item" @click="openBigChart('machine')">
                    <div class="chart-info">
                        <span class="chart-title">机器负载分布</span>
                        <span class="chart-tag">Load</span>
                    </div>
                    <div class="mini-chart-wrapper">
                        <v-chart class="chart-canvas" :option="miniMachineOption" autoresize />
                    </div>
                </div>

                <div class="chart-item" @click="openBigChart('agv')">
                    <div class="chart-info">
                        <span class="chart-title">AGV 任务统计</span>
                        <span class="chart-tag success">Transport</span>
                    </div>
                    <div class="mini-chart-wrapper">
                        <v-chart class="chart-canvas" :option="miniAgvOption" autoresize />
                    </div>
                </div>

                <div class="chart-item" @click="openBigChart('job')">
                    <div class="chart-info">
                        <span class="chart-title">任务延迟趋势</span>
                        <span class="chart-tag warning">Latency</span>
                    </div>
                    <div class="mini-chart-wrapper">
                        <v-chart class="chart-canvas" :option="miniJobOption" autoresize />
                    </div>
                </div>
            </div>
        </div>

        <slot></slot>

        <el-dialog v-model="dialogVisible" :title="currentBigChartTitle" width="60%" align-center append-to-body
            class="chart-dialog">
            <div class="big-chart-container">
                <v-chart class="big-chart" :option="currentBigChartOption" autoresize />
            </div>
        </el-dialog>
    </div>
</template>

<script setup>
import { computed, ref } from 'vue'
import { useMonitorStore } from '@/stores/monitor'
// --- ECharts 引入 ---
import VChart from "vue-echarts";
import { use } from "echarts/core";
import { LineChart, BarChart } from "echarts/charts";
import { CanvasRenderer } from "echarts/renderers";
import {
    TitleComponent,
    TooltipComponent,
    LegendComponent,
    GridComponent,
} from "echarts/components";

use([
    CanvasRenderer,
    LineChart,
    BarChart,
    TitleComponent,
    TooltipComponent,
    LegendComponent,
    GridComponent,
]);

// --- Props (只保留纯 UI 控制的 Props) ---
const props = defineProps({
    title: { type: String, default: '关键指标' },
    showChart: { type: Boolean, default: true }
})

// --- Store ---
const monitorStore = useMonitorStore()

// --- 1. 修复 metricsArray 计算 ---
// 从 store.keyMetrics 转换数组，附加图标和标签
const metricsArray = computed(() => {
    if (!monitorStore.keyMetrics || Object.keys(monitorStore.keyMetrics).length === 0) {
        return []
    }

    // 定义指标的元数据（图标、标签等）
    const metricsMeta = {
        efficiency: {
            label: '生产效率',
            icon: '⚡',
            detail: '设备产出率'
        },
        utilization: {
            label: '设备利用率',
            icon: '🔧',
            detail: '设备运行占比'
        },
        avgLatency: {
            label: '平均延迟',
            icon: '⏱️',
            detail: '任务响应时间'
        },
        throughput: {
            label: '吞吐量',
            icon: '📈',
            detail: '单位时间产量'
        },
        agvCount: {
            label: 'AGV 数量',
            icon: '🤖',
            detail: '在线 AGV 台数'
        },
        machineHealth: {
            label: '设备健康度',
            icon: '❤️',
            detail: '无故障运行率'
        }
    }

    return Object.entries(monitorStore.keyMetrics).map(([key, metric]) => ({
        label: metricsMeta[key]?.label || key,
        icon: metricsMeta[key]?.icon || '📊',
        value: metric.value || '--',
        type: metric.type || 'default',
        detail: metricsMeta[key]?.detail || '',
        key: key
    }))
})

// --- ECharts 配置生成器 ---
const createMiniOption = (type, data, color) => {
    const isLine = type === 'line'
    return {
        grid: { top: 5, bottom: 5, left: 5, right: 5 },
        xAxis: { type: 'category', show: false },
        yAxis: { type: 'value', show: false },
        series: [{
            data: data || [], // 防空保护
            type: type,
            smooth: true,
            showSymbol: false,
            itemStyle: { color: color },
            areaStyle: isLine ? { opacity: 0.2, color: color } : undefined,
            barWidth: '60%'
        }],
        animationDuration: 500
    }
}

const createBigOption = (type, data, labels, title, color) => {
    return {
        title: { text: title, left: 'center' },
        tooltip: { trigger: 'axis' },
        grid: { top: 50, bottom: 30, left: 50, right: 20 },
        xAxis: { type: 'category', data: labels || [] },
        yAxis: { type: 'value' },
        series: [{
            data: data || [],
            type: type,
            smooth: true,
            itemStyle: { color: color },
            barWidth: '40%',
            markLine: type === 'line' ? { data: [{ type: 'average', name: 'Avg' }] } : undefined
        }]
    }
}

// --- 2. 修复迷你图 Options (全部从 Store 读取) ---

// 机器负载
const miniMachineOption = computed(() =>
    createMiniOption('bar', monitorStore.chartData.machine.data, '#667eea')
)

// AGV 负载 (之前报错是因为用了 props.agvData，现在改为 store)
const miniAgvOption = computed(() =>
    createMiniOption('bar', monitorStore.chartData.agv.data, '#4CAF50')
)

// 任务延迟 (改为 store)
const miniJobOption = computed(() =>
    createMiniOption('line', monitorStore.chartData.job.data, '#FF9800')
)

// --- 3. 修复弹窗大图逻辑 ---
const dialogVisible = ref(false)
const currentBigChartTitle = ref('')
const currentBigChartOption = ref({})

const openBigChart = (type) => {
    // 从 Store 获取完整数据 (data + labels)
    const chartData = monitorStore.chartData[type] || { data: [], labels: [] }

    if (type === 'machine') {
        currentBigChartTitle.value = '机器负载详情'
        currentBigChartOption.value = createBigOption('bar', chartData.data, chartData.labels, 'Machine Load', '#667eea')
    } else if (type === 'agv') {
        currentBigChartTitle.value = 'AGV 运输统计'
        currentBigChartOption.value = createBigOption('bar', chartData.data, chartData.labels, 'AGV Load', '#4CAF50')
    } else if (type === 'job') {
        currentBigChartTitle.value = '任务处理延迟趋势'
        currentBigChartOption.value = createBigOption('line', chartData.data, chartData.labels, 'Job Latency (ms)', '#FF9800')
    }
    dialogVisible.value = true
}
</script>

<style scoped>
@import './styles/MetricsPanel.css';
</style>