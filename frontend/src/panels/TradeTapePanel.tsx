import { useTerminalStore } from '../store/useTerminalStore'

export function TradeTapePanel() {
  const { trades, selectedProduct } = useTerminalStore()
  const rows = trades.filter(t => t.symbol === selectedProduct).slice(-20).reverse()
  return <div className='panel'><h3>Trade Tape</h3>{rows.map((t, i) => <div key={i} className='tape'>{t.timestamp} {t.price} x {t.quantity}</div>)}</div>
}
