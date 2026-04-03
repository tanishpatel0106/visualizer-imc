import { HeaderPanel } from '../panels/HeaderPanel'
import { MetricsPanel } from '../panels/MetricsPanel'
import { OrderBookPanel } from '../panels/OrderBookPanel'
import { StrategyPanel } from '../panels/StrategyPanel'
import { TracePanel } from '../panels/TracePanel'
import { TradeTapePanel } from '../panels/TradeTapePanel'

export function App() {
  return <div className='terminal'>
    <HeaderPanel />
    <div className='grid'>
      <OrderBookPanel />
      <StrategyPanel />
      <MetricsPanel />
    </div>
    <div className='grid bottom'>
      <TradeTapePanel />
      <TracePanel />
    </div>
  </div>
}
