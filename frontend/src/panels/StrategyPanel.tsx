import { useTerminalStore } from '../store/useTerminalStore'

export function StrategyPanel() {
  const { strategies, runBacktest } = useTerminalStore()
  return <div className='panel'><h3>Built-in Strategy Library</h3>
    {strategies.slice(0, 15).map((s) => <div key={s.id} className='strategyRow'>
      <div><b>{s.name}</b><div className='muted'>{s.meta?.category}</div></div>
      <button onClick={() => runBacktest(s.id, 'balanced')}>Run</button>
    </div>)}
  </div>
}
