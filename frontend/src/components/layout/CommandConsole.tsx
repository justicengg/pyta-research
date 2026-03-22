import type { RoundRecord } from '../../lib/types/canvas'
import type { SandboxInputEvent } from '../../lib/types/sandbox'

type Props = {
  draft: string
  onDraftChange: (value: string) => void
  onSubmit: () => void
  isRunning: boolean
  error: string | null
  currentRound: number
  roundHistory: RoundRecord[]
  currentInputEvents: SandboxInputEvent[]
}

export function CommandConsole({
  draft,
  onDraftChange,
  onSubmit,
  isRunning,
  error,
  currentRound,
  roundHistory,
  currentInputEvents,
}: Props) {
  const hasHistory = roundHistory.length > 0
  const lastRound = roundHistory[roundHistory.length - 1]

  const qualityText =
    lastRound?.quality === 'complete' ? '已收敛' :
    lastRound?.quality === 'partial'  ? '部分收敛' : '待优化'

  return (
    <section className="command">

      {/* ── Timeline (always visible after first run) ────────────── */}
      {hasHistory && (
        <div className="cmd-timeline">
          {roundHistory.map((r) => (
            <span
              key={r.round}
              className="cmd-dot cmd-dot--done"
              title={`第 ${r.round} 轮: ${r.narrative.slice(0, 50)}`}
            >
              {r.round}
            </span>
          ))}
          <span className="cmd-dot cmd-dot--next">{currentRound}</span>
          <span className="cmd-round-label">第 {currentRound} 轮推演</span>
          {lastRound && (
            <span className={`cmd-quality cmd-quality--${lastRound.quality}`}>
              {qualityText}
            </span>
          )}
        </div>
      )}

      {/* ── Two-zone layout ──────────────────────────────────────── */}
      <div className="cmd-body">

        {/* Left: context chips */}
        <div className="cmd-context">
          <p className="cmd-context-label">上下文</p>
          <div className="cmd-chips">

            {/* Events chip — shows when events have been loaded */}
            {currentInputEvents.length > 0 && (
              <span className="cmd-chip cmd-chip--events">
                <span className="cmd-chip-dot" />
                事件
                <span className="cmd-chip-count">{currentInputEvents.length}</span>
              </span>
            )}

            {/* History chip — shows previous rounds */}
            {hasHistory && (
              <span className="cmd-chip cmd-chip--history">
                <span className="cmd-chip-dot" />
                历史轮次
                <span className="cmd-chip-count">{roundHistory.length}</span>
              </span>
            )}

            {/* 5 agents always active */}
            <span className="cmd-chip cmd-chip--agents">
              <span className="cmd-chip-dot" />
              5 Agents
            </span>

            {/* Empty state hint */}
            {currentInputEvents.length === 0 && !hasHistory && (
              <span className="cmd-context-empty">暂无上下文，运行后自动记录</span>
            )}
          </div>

          {/* Previous round summary hint */}
          {lastRound && (
            <div className="cmd-prev-hint">
              <span className="cmd-prev-label">上轮</span>
              <span className="cmd-prev-text">
                {Object.values(lastRound.agentSummaries)[0]?.slice(0, 72)}…
              </span>
            </div>
          )}
        </div>

        {/* Right: textarea + actions */}
        <div className="cmd-input">
          <textarea
            value={draft}
            onChange={(e) => onDraftChange(e.target.value)}
            placeholder={
              hasHistory
                ? `基于第 ${currentRound - 1} 轮结果，输入下一轮推演指令…`
                : '输入推演指令，Enter 运行，Shift+Enter 换行。'
            }
            onKeyDown={(e) => {
              if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault()
                onSubmit()
              }
            }}
          />
          <div className="cmd-actions">
            <button className="plus-btn" aria-label="添加上下文" type="button">+</button>
            <select className="mode-select" aria-label="模式" defaultValue="minimal">
              <option value="minimal">极简模式</option>
              <option value="expert">专家模式</option>
            </select>
            <button
              className="run-btn"
              type="button"
              onClick={onSubmit}
              disabled={isRunning || !draft.trim()}
            >
              {isRunning ? '推演中…' : hasHistory ? `▶ 第 ${currentRound} 轮` : '▶ 运行推演'}
            </button>
          </div>
        </div>
      </div>

      {error && <p className="command-error">{error}</p>}
    </section>
  )
}
