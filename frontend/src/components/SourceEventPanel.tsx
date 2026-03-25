import { useMemo, useState } from 'react'
import { useSourceEvents } from '../hooks/useSourceEvents'
import type { SourceEvent } from '../lib/types/sourceEvents'

type Props = {
  ticker: string
  onConfirm: (selectedEvents: SourceEvent[]) => void
  onClose: () => void
}

function ImpactDot({ direction }: { direction: SourceEvent['impact_direction'] }) {
  const color =
    direction === 'positive' ? 'var(--accent)' :
    direction === 'negative' ? '#c44949' :
    'var(--text-3)'
  return <span className="ep-event-dot" style={{ background: color }} />
}

function formatEventTime(value: string | null): string {
  if (!value) return '未知时间'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) {
    return value
  }
  return date.toLocaleString()
}

export function SourceEventPanel({ ticker, onConfirm, onClose }: Props) {
  const { items, total, isLoading, error, refetch } = useSourceEvents({
    symbol: ticker,
    limit: 20,
  })
  const [selectedIds, setSelectedIds] = useState<string[]>([])

  const selectedEvents = useMemo(
    () => items.filter((event) => selectedIds.includes(event.id)),
    [items, selectedIds],
  )

  function toggleEvent(eventId: string) {
    setSelectedIds((current) => (
      current.includes(eventId)
        ? current.filter((id) => id !== eventId)
        : [...current, eventId]
    ))
  }

  return (
    <div className="events-panel events-panel--open">
      <div className="ep-header">
        <span className="ep-title">{ticker} 相关信号</span>
        <span className="ep-count">{total} 条</span>
        <button className="ep-close" onClick={onClose} aria-label="关闭信号面板">✕</button>
      </div>

      <div className="ep-body">
        {isLoading ? (
          <p className="ep-empty">loading</p>
        ) : error ? (
          <div className="ep-empty">
            <p>加载失败</p>
            <button className="run-btn" type="button" onClick={() => void refetch()}>
              重试
            </button>
          </div>
        ) : items.length === 0 ? (
          <p className="ep-empty">暂无匹配信号</p>
        ) : (
          items.map((event) => {
            const checked = selectedIds.includes(event.id)
            return (
              <label
                key={event.id}
                className={`ep-event${checked ? ' ep-event--selected' : ''}`}
                title={event.dimension ?? event.provider_id}
              >
                <input
                  type="checkbox"
                  checked={checked}
                  onChange={() => toggleEvent(event.id)}
                />
                <ImpactDot direction={event.impact_direction} />
                <span className="ep-event-title">
                  <strong>{event.provider_id}</strong>
                  <br />
                  {event.title}
                  <br />
                  <small>{formatEventTime(event.published_at ?? event.ingested_at)} · {event.impact_direction}</small>
                </span>
              </label>
            )
          })
        )}
      </div>

      <div className="ep-footer">
        <span className="ep-footer-hint">已选 {selectedEvents.length} 条</span>
        <button className="run-btn" type="button" onClick={() => onConfirm(selectedEvents)}>
          Run →
        </button>
      </div>
    </div>
  )
}
