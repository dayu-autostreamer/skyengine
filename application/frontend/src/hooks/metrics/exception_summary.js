/**
 * 异常事件累计 Hook
 * 数据源：metricsTimeline[].metrics 中由 sim_server 合并进来的 event_metrics。
 */
const SERIES = [
  { key: 'event_count_total', name: '异常总数', color: '#ff6464' },
  { key: 'machine_failure_count', name: '机器故障', color: '#ff8a65' },
  { key: 'agv_failure_count', name: 'AGV 故障', color: '#ffb450' },
  { key: 'temporary_obstacle_count', name: '临时障碍', color: '#ba68c8' },
]

export default {
  id: 'exception_summary',
  label: '异常累计',
  unit: 'count',
  multiSeries: true,
  series: (ctx) => {
    const points = ctx.metrics || []
    return SERIES.map((def) => ({
      name: def.name,
      color: def.color,
      data: points
        .map((p, idx) => ({
          x: p?.step ?? idx,
          y: Number(p?.metrics?.[def.key] ?? 0),
        }))
        .filter((p) => Number.isFinite(p.y)),
    }))
  },
}
