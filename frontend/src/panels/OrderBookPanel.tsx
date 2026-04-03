import { useMemo } from 'react'
import { useTerminalStore } from '../store/useTerminalStore'

export function OrderBookPanel() {
  const { snapshots, selectedProduct } = useTerminalStore()
  const latest = useMemo(() => snapshots.filter(s => s.product === selectedProduct).slice(-1)[0], [snapshots, selectedProduct])
  if (!latest) return <div className='panel'>No book</div>
  return <div className='panel'>
    <h3>Order Book Ladder</h3>
    <div>Best Bid: {latest.bid_price_1} x {latest.bid_volume_1}</div>
    <div>Best Ask: {latest.ask_price_1} x {latest.ask_volume_1}</div>
    <div>Spread: {(latest.ask_price_1 - latest.bid_price_1).toFixed(2)}</div>
    {[1,2,3].map(i => <div key={i} className='ladderRow'>
      <span className='bid'>{latest[`bid_price_${i}`]} ({latest[`bid_volume_${i}`]})</span>
      <span className='ask'>{latest[`ask_price_${i}`]} ({latest[`ask_volume_${i}`]})</span>
    </div>)}
  </div>
}
