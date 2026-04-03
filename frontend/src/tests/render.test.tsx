import { describe, it, expect } from 'vitest'
import { render } from '@testing-library/react'
import { MetricsPanel } from '../panels/MetricsPanel'

describe('metrics', () => {
  it('renders panel', () => {
    const { getByText } = render(<MetricsPanel />)
    expect(getByText(/No run yet/i)).toBeTruthy()
  })
})
