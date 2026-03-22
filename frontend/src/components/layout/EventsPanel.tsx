import { useEffect, useState } from 'react'

type SourceEvent = {
  id: string
  provider_id: string
  title: string
  dimension: string | null
  impact_direction: 'positive' | 'negative' | 'neutral'
  impact_strength: number
}

type Props = {
  isOpen: boolean
  onClose: () => void
  onSelectEvent: (title: string) => void
}

function ImpactDot({ direction }: { direction: SourceEvent['impact_direction'] }) {
  const color =
    direction === 'positive' ? 'var(--accent)' :
    direction === 'negative' ? '#c44949' :
    'var(--text-3)'
  return <span className="ep-event-dot" style={{ background: color }} />
}

export function EventsPanel({ isOpen, onClose, onSelectEvent }: Props) {
  const [events, setEvents] = useState<SourceEvent[]>([])
  const [selected, setSelected] = useState<string | null>(null)

  useEffect(() => {
    fetch('/api/v1/sources/events?limit=20')
      .then((r) => r.ok ? r.json() : [])
      .then(setEvents)
      .catch(() => setEvents([]))
  }, [])

  function handleSelect(event: SourceEvent) {
    setSelected(event.id)
    onSelectEvent(event.title)
    onClose()
  }

  return (
    <div className={`events-panel${isOpen ? ' events-panel--open' : ''}`} aria-hidden={!isOpen}>
      <div className="ep-header">
        <span className="ep-title">事件上下文</span>
        <span className="ep-count">{events.length} 条</span>
        <button className="ep-close" onClick={onClose} aria-label="关闭事件面板">✕</button>
      </div>

      <div className="ep-body">
        {events.length === 0 ? (
          <p className="ep-empty">暂无事件数据</p>
        ) : (
          events.map((e) => (
            <button
              key={e.id}
              className={`ep-event${selected === e.id ? ' ep-event--selected' : ''}`}
              onClick={() => handleSelect(e)}
              title={e.dimension ?? e.provider_id}
            >
              <ImpactDot direction={e.impact_direction} />
              <span className="ep-event-title">{e.title}</span>
            </button>
          ))
        )}
      </div>

      <div className="ep-footer">
        <span className="ep-footer-hint">点击事件 → 填入指令框</span>
      </div>
    </div>
  )
}
