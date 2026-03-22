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
  onSelect: (title: string) => void
}

function ImpactDot({ direction }: { direction: SourceEvent['impact_direction'] }) {
  const color =
    direction === 'positive' ? 'var(--accent)' :
    direction === 'negative' ? '#c44949' :
    'var(--text-3)'
  return <span className="event-chip-dot" style={{ background: color }} />
}

export function EventChips({ onSelect }: Props) {
  const [events, setEvents] = useState<SourceEvent[]>([])
  const [selected, setSelected] = useState<string | null>(null)

  useEffect(() => {
    fetch('/api/v1/sources/events?limit=5')
      .then((r) => r.ok ? r.json() : [])
      .then(setEvents)
      .catch(() => setEvents([]))
  }, [])

  if (events.length === 0) return null

  function handleClick(event: SourceEvent) {
    setSelected(event.id)
    onSelect(event.title)
  }

  return (
    <div className="event-chips-bar">
      <span className="event-chips-label">Events</span>
      <div className="event-chips-list">
        {events.map((e) => (
          <button
            key={e.id}
            className={`event-chip${selected === e.id ? ' selected' : ''}`}
            onClick={() => handleClick(e)}
            title={e.dimension ?? e.provider_id}
          >
            <ImpactDot direction={e.impact_direction} />
            <span className="event-chip-title">{e.title}</span>
          </button>
        ))}
      </div>
    </div>
  )
}
