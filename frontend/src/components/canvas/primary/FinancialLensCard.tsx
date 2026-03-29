import type { FinancialLensData } from '../../../lib/types/primaryCanvas'

type Props = {
  data: FinancialLensData
  position: { x: number; y: number }
  onDragMove: (dx: number, dy: number) => void
}

function fmt(val: number | undefined, prefix = '', suffix = ''): string {
  if (val == null) return '—'
  return `${prefix}${val.toLocaleString()}${suffix}`
}

function fmtUSD(val: number | undefined): string {
  if (val == null) return '—'
  if (val >= 1_000_000) return `$${(val / 1_000_000).toFixed(1)}M`
  if (val >= 1_000) return `$${(val / 1_000).toFixed(0)}K`
  return `$${val}`
}

export function FinancialLensCard({ data, position, onDragMove }: Props) {
  const dragRef = { active: false, lastX: 0, lastY: 0 }

  function handlePointerDown(e: React.PointerEvent<HTMLDivElement>) {
    if (e.button !== 0) return
    const target = e.target as HTMLElement
    if (target.closest('button, input, textarea, select, a')) return
    e.stopPropagation()
    e.currentTarget.setPointerCapture(e.pointerId)
    dragRef.active = true
    dragRef.lastX = e.clientX
    dragRef.lastY = e.clientY
  }

  function handlePointerMove(e: React.PointerEvent<HTMLDivElement>) {
    if (!dragRef.active) return
    const dx = e.clientX - dragRef.lastX
    const dy = e.clientY - dragRef.lastY
    dragRef.lastX = e.clientX
    dragRef.lastY = e.clientY
    onDragMove(dx, dy)
  }

  function handlePointerUp() { dragRef.active = false }

  const metrics = [
    { label: 'ARR',          value: fmtUSD(data.arr) },
    { label: 'NRR',          value: fmt(data.nrr, '', '%') },
    { label: '毛利率',        value: fmt(data.grossMargin, '', '%') },
    { label: '月烧钱',        value: fmtUSD(data.monthlyBurn) },
    { label: 'LTV / CAC',   value: fmt(data.ltvCacRatio, '', 'x') },
    { label: '当前估值',      value: fmtUSD(data.currentValuation) },
    { label: 'Runway',       value: fmt(data.runwayMonths, '', ' 个月') },
  ]

  return (
    <div
      className="pm-card pm-card--financial"
      style={{ left: position.x, top: position.y }}
      data-no-pan
      onPointerDown={handlePointerDown}
      onPointerMove={handlePointerMove}
      onPointerUp={handlePointerUp}
      onPointerCancel={handlePointerUp}
    >
      <div className="pm-card__header">
        <span className="pm-card__label">模块 4</span>
        <h3 className="pm-card__title">财务透视</h3>
      </div>

      <div className="pm-card__body">
        <div className="pm-financial-grid">
          {metrics.map(({ label, value }) => (
            <div key={label} className="pm-financial-item">
              <span className="pm-financial-label">{label}</span>
              <span className="pm-financial-value">{value}</span>
            </div>
          ))}
        </div>
        {data.valuationNarrative && (
          <p className="pm-card__narrative">{data.valuationNarrative}</p>
        )}
      </div>
    </div>
  )
}
