import type { RoundRecord } from '../../lib/types/canvas'

type Props = {
  draft: string
  onDraftChange: (value: string) => void
  onSubmit: () => void
  isRunning: boolean
  error: string | null
  currentRound: number
  roundHistory: RoundRecord[]
}

export function CommandConsole({
  draft,
  onDraftChange,
  onSubmit,
  isRunning,
  error,
  currentRound,
  roundHistory,
}: Props) {
  const hasHistory = roundHistory.length > 0
  const lastRound = roundHistory[roundHistory.length - 1]

  return (
    <section className="command">
      {/* Round timeline — shows only after at least one run */}
      {hasHistory && (
        <div className="round-timeline">
          {roundHistory.map((r) => (
            <span key={r.round} className="round-dot round-dot--done" title={`第 ${r.round} 轮: ${r.narrative.slice(0, 40)}`}>
              {r.round}
            </span>
          ))}
          <span className="round-dot round-dot--next">
            {currentRound}
          </span>
          <span className="round-label">第 {currentRound} 轮推演</span>
          {lastRound && (
            <span className={`round-quality round-quality--${lastRound.quality}`}>
              {lastRound.quality === 'complete' ? '已收敛' : lastRound.quality === 'partial' ? '部分收敛' : '待优化'}
            </span>
          )}
        </div>
      )}

      <div className="command-box">
        {/* Previous round context hint */}
        {lastRound && (
          <div className="prev-round-hint">
            <span className="prev-round-label">上轮要点</span>
            <span className="prev-round-text">
              {Object.values(lastRound.agentSummaries)[0]?.slice(0, 80)}…
            </span>
          </div>
        )}

        <textarea
          value={draft}
          onChange={(event) => onDraftChange(event.target.value)}
          placeholder={
            hasHistory
              ? `基于第 ${currentRound - 1} 轮结果，继续推演…`
              : '输入你的下一步操作，回车运行，Shift + Enter 换行。'
          }
          onKeyDown={(e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
              e.preventDefault()
              onSubmit()
            }
          }}
        />
        <div className="composer-tools">
          <div className="plus-wrap">
            <button className="plus-btn" aria-label="打开功能菜单" type="button">+</button>
          </div>
          <select className="mode-select" aria-label="模式切换" defaultValue="极简模式">
            <option>极简模式</option>
            <option>专家模式</option>
          </select>
          <button
            className="run-btn"
            type="button"
            onClick={onSubmit}
            disabled={isRunning || !draft.trim()}
          >
            {isRunning ? '推演中…' : hasHistory ? `▶ 第 ${currentRound} 轮推演` : '▶ 运行推演'}
          </button>
        </div>
        {error ? <p className="command-error">{error}</p> : null}
      </div>
    </section>
  )
}
