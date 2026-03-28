import type { SandboxEnvironmentState } from '../../lib/types/sandbox'

type Props = {
  state: SandboxEnvironmentState | null
}

export function EnvironmentBar({ state }: Props) {
  if (!state) {
    return null
  }

  return (
    <div className="environment-bar" aria-label="Environment Bar">
      <div className="environment-bar-meta">
        <span className="environment-bar-label">Environment Bar</span>
        <span className={`environment-risk environment-risk--${state.globalRiskTone}`}>
          {renderRiskTone(state.globalRiskTone)}
        </span>
      </div>
      <div className="environment-chip-row">
        {state.buckets.map((bucket) => (
          <div
            key={bucket.type}
            className={`environment-chip environment-chip--${bucket.status} environment-chip--${bucket.dominantDirection}`}
          >
            <span className="environment-chip-title">{bucket.displayName}</span>
            <span className="environment-chip-metrics">
              {bucket.activeSignals.length} signals · {bucket.aggregateStrength}
            </span>
          </div>
        ))}
      </div>
    </div>
  )
}

function renderRiskTone(riskTone: SandboxEnvironmentState['globalRiskTone']): string {
  switch (riskTone) {
    case 'risk_on':
      return 'Risk-on'
    case 'risk_off':
      return 'Risk-off'
    case 'mixed':
      return 'Mixed'
    default:
      return 'Neutral'
  }
}
