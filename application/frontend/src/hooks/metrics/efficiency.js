/**
 * 系统效率 Hook
 * 数据源：metrics point 里的 metrics.efficiency (0-1)
 * 若后端未显式给出 efficiency，则退化使用 agv_loaded_utilization。
 * Canonical shape: { step, metrics:{ efficiency, ... }, metrics_reward }
 */
export default {
  id: 'efficiency',
  label: '系统效率',
  unit: '%',
  series: (ctx) => {
    const metrics = ctx.metrics || []
    const data = metrics
      .map((p, idx) => {
        const raw = p?.metrics?.efficiency ?? p?.metrics?.agv_loaded_utilization
        if (typeof raw !== 'number') return null
        return {
          x: p?.step ?? idx,
          y: Math.round(raw * 10000) / 100,
        }
      })
      .filter(Boolean)
    return [{ name: '系统效率', data, color: '#64b5ff' }]
  },
}
