/**
 * 机器利用率 Hook
 * 数据源：metrics point 里的 metrics.machine_utilization (0-1)
 * Canonical shape: { step, metrics:{ machine_utilization, ... }, metrics_reward }
 */
export default {
  id: 'machine_util',
  label: '机器利用率',
  unit: '%',
  series: (ctx) => {
    const metrics = ctx.metrics || []
    const data = metrics
      .map((p, idx) => {
        const raw = p?.metrics?.machine_utilization
        if (typeof raw !== 'number') return null
        return {
          x: p?.step ?? idx,
          y: Math.round(raw * 10000) / 100,
        }
      })
      .filter(Boolean)
    return [{ name: '机器利用率', data, color: '#66d06a' }]
  },
}
