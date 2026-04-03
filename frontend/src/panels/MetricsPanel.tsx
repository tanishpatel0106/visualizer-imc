import { useTerminalStore } from '../store/useTerminalStore'

export function MetricsPanel() {
  const { run } = useTerminalStore()
  if (!run) return <div className='panel'>No run yet</div>
  const m = run.run.metrics
  return <div className='panel'><h3>Run Metrics</h3>
    {Object.entries(m).map(([k,v]) => <div key={k} className='metric'><span>{k}</span><span>{String(v)}</span></div>)}
  </div>
}
