import { useTerminalStore } from '../store/useTerminalStore'

export function TracePanel() {
  const { run } = useTerminalStore()
  const frames = run?.run?.debug_trace || []
  return <div className='panel'><h3>Debugger / Trace</h3>
    <div className='traceBox'>
      {frames.slice(0, 120).map((f: any, i: number) => <div key={i} className='traceLine'>{f.timestamp} {f.product} spread={f.spread} pos={f.position} pnl={f.pnl_total}</div>)}
    </div>
  </div>
}
