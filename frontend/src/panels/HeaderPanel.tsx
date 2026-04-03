import { useEffect } from 'react'
import { useTerminalStore } from '../store/useTerminalStore'

export function HeaderPanel() {
  const { products, days, selectedProduct, selectedDay, loadAll, strategies, runBacktest } = useTerminalStore()
  useEffect(() => { loadAll() }, [loadAll])
  return <div className='panel header'>
    <div className='badge'>DATASET: sample_data</div>
    <div className='badge'>PRODUCT: {selectedProduct}</div>
    <div className='badge'>DAY: {selectedDay ?? '-'}</div>
    <div className='badge'>STRATS: {strategies.length}</div>
    <button onClick={() => runBacktest('imbalance_follow', 'balanced')}>Quick Run</button>
    <div className='badge'>PRODS {products.join(',')}</div>
    <div className='badge'>DAYS {days.join(',')}</div>
  </div>
}
