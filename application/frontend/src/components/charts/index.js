/**
 * Chart 模板注册表
 *
 * 模板契约：
 * - 每个模板接收统一的 series 格式 [{name, data:[{x,y}], color?}]
 * - 不感知指标名，仅负责"用哪种图形渲染这堆数据"
 *
 * 配置层（dashboard JSON）通过 `template: "line" | "bar"` 字符串引用，
 * DashboardPanel 用 templateMap 解析到具体组件。
 */
import LineChart from './LineChart.vue'
import BarChart from './BarChart.vue'
import HorizontalBarChart from './HorizontalBarChart.vue'

export const TEMPLATES = {
  line: LineChart,
  bar: BarChart,
  'horizontal-bar': HorizontalBarChart,
}

export function getTemplate(name) {
  return TEMPLATES[name] || null
}

export function listTemplates() {
  return Object.keys(TEMPLATES)
}
