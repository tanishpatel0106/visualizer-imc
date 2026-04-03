import { describe, it, expect } from 'vitest'
import { useTerminalStore } from '../store/useTerminalStore'

describe('store', () => {
  it('has defaults', () => {
    const s = useTerminalStore.getState()
    expect(s.selectedProduct).toBe('EMERALDS')
  })
})
