import { create } from 'zustand'
import api from '../services/api'

interface State {
  products: string[]
  days: number[]
  snapshots: any[]
  trades: any[]
  strategies: any[]
  selectedProduct: string
  selectedDay: number | null
  run: any | null
  loadAll: () => Promise<void>
  runBacktest: (strategyId: string, executionModel: string) => Promise<void>
}

export const useTerminalStore = create<State>((set, get) => ({
  products: [], days: [], snapshots: [], trades: [], strategies: [], selectedProduct: 'EMERALDS', selectedDay: null, run: null,
  loadAll: async () => {
    await api.post('/datasets/load', { dataset_id: 'sample', path: 'sample_data' })
    const [p, d, s, t, st] = await Promise.all([
      api.get('/products'), api.get('/days'), api.get('/snapshots'), api.get('/trades'), api.get('/strategies')
    ])
    set({ products: p.data, days: d.data, snapshots: s.data, trades: t.data, strategies: st.data, selectedProduct: p.data[0] || 'EMERALDS', selectedDay: d.data[0] ?? null })
  },
  runBacktest: async (strategyId, executionModel) => {
    const state = get()
    const r = await api.post('/backtest/run', { strategy_id: strategyId, execution_model: executionModel, products: [state.selectedProduct], days: state.selectedDay !== null ? [state.selectedDay] : [] })
    set({ run: r.data })
  }
}))
