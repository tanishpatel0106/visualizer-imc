import { useEffect } from 'react'
import { useTerminalStore } from '../store/useTerminalStore'

export function HeaderPanel() {
  const { products, days, selectedProduct, selectedDay, loadAll, strategies, runBacktest, setProduct, setDay, loadError, loading } = useTerminalStore()
  useEffect(() => { loadAll() }, [loadAll])
  return <div className='panel header'>
    <div className='badge'>DATASET: sample_data</div>
    <label className='badge'>PRODUCT:
      <select value={selectedProduct} onChange={(e) => setProduct(e.target.value)}>
        {products.map(p => <option key={p} value={p}>{p}</option>)}
      </select>
    </label>
    <label className='badge'>DAY:
      <select value={selectedDay ?? ''} onChange={(e) => setDay(e.target.value === '' ? null : Number(e.target.value))}>
        {days.map(d => <option key={d} value={d}>{d}</option>)}
      </select>
    </label>
    <div className='badge'>STRATS: {strategies.length}</div>
    <button onClick={() => runBacktest('imbalance_follow', 'balanced')}>Quick Run</button>
    <div className='badge'>{loading ? 'LOADING…' : 'READY'}</div>
    {loadError ? <div className='badge error'>LOAD ERROR: {loadError}</div> : null}
    <div className='badge'>PRODS {products.join(',')}</div>
    <div className='badge'>DAYS {days.join(',')}</div>
  </div>
}
