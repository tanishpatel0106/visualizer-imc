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
  loadError: string | null
  loading: boolean
  setProduct: (p: string) => Promise<void>
  setDay: (d: number | null) => Promise<void>
  loadAll: () => Promise<void>
  runBacktest: (strategyId: string, executionModel: string) => Promise<void>
}

export const useTerminalStore = create<State>((set, get) => ({
  products: [], days: [], snapshots: [], trades: [], strategies: [], selectedProduct: 'EMERALDS', selectedDay: null, run: null, loadError: null, loading: false,
  loadAll: async () => {
    try {
      set({ loading: true, loadError: null })
      await api.post('/datasets/load', { dataset_id: 'sample', path: 'sample_data' })
      const [p, d, st] = await Promise.all([api.get('/products'), api.get('/days'), api.get('/strategies')])
      const product = p.data[0] || 'EMERALDS'
      const day = d.data[0] ?? null
      const [s, t] = await Promise.all([
        api.get('/snapshots', { params: { product, day } }),
        api.get('/trades', { params: { product, day } })
      ])
      set({ products: p.data, days: d.data, snapshots: s.data, trades: t.data, strategies: st.data, selectedProduct: product, selectedDay: day, loading: false })
    } catch (e: any) {
      set({ loading: false, loadError: e?.response?.data?.detail || e?.message || 'dataset load failed' })
    }
  },
  setProduct: async (p) => {
    const d = get().selectedDay
    const [s, t] = await Promise.all([api.get('/snapshots', { params: { product: p, day: d } }), api.get('/trades', { params: { product: p, day: d } })])
    set({ selectedProduct: p, snapshots: s.data, trades: t.data })
  },
  setDay: async (d) => {
    const p = get().selectedProduct
    const [s, t] = await Promise.all([api.get('/snapshots', { params: { product: p, day: d } }), api.get('/trades', { params: { product: p, day: d } })])
    set({ selectedDay: d, snapshots: s.data, trades: t.data })
  },
  runBacktest: async (strategyId, executionModel) => {
    const state = get()
    const r = await api.post('/backtest/run', { strategy_id: strategyId, execution_model: executionModel, products: [state.selectedProduct], days: state.selectedDay !== null ? [state.selectedDay] : [] })
    set({ run: r.data })
  }
}))
