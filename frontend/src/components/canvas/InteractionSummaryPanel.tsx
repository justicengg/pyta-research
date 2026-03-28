import type { CanvasInteractionResolution, SandboxAgentId } from '../../lib/types/sandbox'

type Props = {
  resolution: CanvasInteractionResolution | null
  onHighlightAgents: (agentIds: SandboxAgentId[]) => void
  onClearHighlight: () => void
}

const REGIME_LABEL: Record<CanvasInteractionResolution['marketForceSummary']['regime'], string> = {
  expansion: '扩张',
  contraction: '收缩',
  fragmented: '分裂',
  balanced: '平衡',
}

const BIAS_LABEL: Record<CanvasInteractionResolution['marketForceSummary']['netBias'], string> = {
  bullish: '偏多',
  bearish: '偏空',
  mixed: '混合',
  neutral: '中性',
}

const AGENT_LABEL: Record<SandboxAgentId, string> = {
  traditional_institution: '传统机构',
  quant_institution: '量化机构',
  retail: '普通散户',
  offshore_capital: '海外资金',
  short_term_capital: '游资 / 短线',
}

export function InteractionSummaryPanel({ resolution, onHighlightAgents, onClearHighlight }: Props) {
  if (!resolution) {
    return null
  }

  const summary = resolution.marketForceSummary

  return (
    <aside className="interaction-panel" data-no-pan>
      <div className="interaction-panel__header">
        <div>
          <strong>市场力量博弈</strong>
          <p>{summary.summary}</p>
        </div>
        <div className="interaction-panel__pills">
          <span className={`interaction-pill interaction-pill--${summary.regime}`}>{REGIME_LABEL[summary.regime]}</span>
          <span className={`interaction-pill interaction-pill--${summary.netBias}`}>{BIAS_LABEL[summary.netBias]}</span>
        </div>
      </div>

      <div className="interaction-panel__metrics">
        <div className="interaction-metric">
          <span>多头压力</span>
          <strong>{summary.bullishPressure.toFixed(2)}</strong>
        </div>
        <div className="interaction-metric">
          <span>空头压力</span>
          <strong>{summary.bearishPressure.toFixed(2)}</strong>
        </div>
      </div>

      <div className="interaction-panel__group">
        <span className="interaction-panel__label">主导力量</span>
        <div className="interaction-chip-row">
          {summary.dominantAgents.map((agentId) => (
            <button
              key={agentId}
              className="interaction-chip"
              onMouseEnter={() => onHighlightAgents([agentId])}
              onMouseLeave={onClearHighlight}
              type="button"
            >
              {AGENT_LABEL[agentId]}
            </button>
          ))}
        </div>
      </div>

      <div className="interaction-panel__columns">
        <div className="interaction-panel__column">
          <span className="interaction-panel__label">强化关系</span>
          {resolution.reinforcements.slice(0, 2).map((item) => (
            <button
              key={`${item.between.join('-')}-${item.description}`}
              className="interaction-item interaction-item--reinforce"
              onMouseEnter={() => onHighlightAgents(item.between)}
              onMouseLeave={onClearHighlight}
              type="button"
            >
              <strong>{item.between.map((agentId) => AGENT_LABEL[agentId]).join(' × ')}</strong>
              <span>{item.description}</span>
            </button>
          ))}
        </div>

        <div className="interaction-panel__column">
          <span className="interaction-panel__label">冲突关系</span>
          {resolution.conflicts.slice(0, 2).map((item) => (
            <button
              key={`${item.between.join('-')}-${item.description}`}
              className="interaction-item interaction-item--conflict"
              onMouseEnter={() => onHighlightAgents(item.between)}
              onMouseLeave={onClearHighlight}
              type="button"
            >
              <strong>{item.between.map((agentId) => AGENT_LABEL[agentId]).join(' × ')}</strong>
              <span>{item.description}</span>
            </button>
          ))}
        </div>
      </div>
    </aside>
  )
}
