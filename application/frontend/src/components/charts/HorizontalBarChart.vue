<template>
  <div class="horizontal-bar-chart-wrap">
    <v-chart
      v-if="hasData"
      :option="chartOption"
      :autoresize="true"
      class="horizontal-bar-chart"
    />
    <div v-else class="empty-chart">
      <span>暂无数据</span>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { BarChart } from 'echarts/charts'
import { GridComponent, TooltipComponent, LegendComponent } from 'echarts/components'
import VChart from 'vue-echarts'

use([CanvasRenderer, BarChart, GridComponent, TooltipComponent, LegendComponent])

const props = defineProps({
  series: { type: Array, default: () => [] },
  xLabel: { type: String, default: '' },
  yLabel: { type: String, default: '' },
  yMax: { type: Number, default: null },
  height: { type: String, default: '300px' },
})

const hasData = computed(() =>
  props.series.some((series) => Array.isArray(series.data) && series.data.length > 0),
)

const chartOption = computed(() => {
  const categories = []
  const seen = new Set()
  props.series.forEach((series) => {
    ;(series.data || []).forEach((point) => {
      if (!seen.has(point.x)) {
        seen.add(point.x)
        categories.push(point.x)
      }
    })
  })

  const series = props.series.map((item) => {
    const values = new Map((item.data || []).map((point) => [point.x, point.y]))
    return {
      name: item.name || '',
      type: 'bar',
      barMaxWidth: 14,
      itemStyle: {
        color: item.color,
        borderRadius: [0, 3, 3, 0],
      },
      label: {
        show: true,
        position: 'right',
        color: 'rgba(220, 230, 245, 0.72)',
        fontSize: 9,
      },
      data: categories.map((category) => values.get(category) ?? null),
    }
  })

  return {
    grid: { left: 68, right: 34, top: 34, bottom: 28 },
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'shadow' },
      backgroundColor: 'rgba(20, 26, 48, 0.94)',
      borderColor: 'rgba(100, 180, 255, 0.3)',
      textStyle: { color: '#dce4f0', fontSize: 11 },
    },
    legend: {
      top: 4,
      textStyle: { color: 'rgba(200, 220, 255, 0.7)', fontSize: 10 },
    },
    xAxis: {
      type: 'value',
      name: props.yLabel || props.xLabel,
      max: props.yMax ?? null,
      axisLabel: { color: 'rgba(160, 190, 230, 0.5)', fontSize: 10 },
      axisLine: { lineStyle: { color: 'rgba(100, 180, 255, 0.15)' } },
      splitLine: { lineStyle: { color: 'rgba(100, 180, 255, 0.06)' } },
    },
    yAxis: {
      type: 'category',
      inverse: true,
      data: categories,
      axisTick: { show: false },
      axisLine: { lineStyle: { color: 'rgba(100, 180, 255, 0.15)' } },
      axisLabel: {
        color: 'rgba(210, 225, 245, 0.78)',
        fontSize: 10,
        width: 58,
        overflow: 'truncate',
      },
    },
    series,
  }
})
</script>

<style scoped>
.horizontal-bar-chart-wrap,
.horizontal-bar-chart {
  width: 100%;
  height: v-bind('height');
}

.empty-chart {
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  color: rgba(160, 190, 230, 0.3);
  font-size: 12px;
}
</style>
