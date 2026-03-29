import type { ReactNode } from 'react'

type Props = {
  draft: string
  onDraftChange: (value: string) => void
  onSubmit: () => void
  isRunning: boolean
  error: string | null
  roundsCompleted: number
  stopReason: string | null
  promptMascot?: ReactNode
}

export function PrimaryCommandConsole({
  draft,
  onDraftChange,
  onSubmit,
  isRunning,
  error,
  roundsCompleted,
  stopReason,
  promptMascot,
}: Props) {
  const hasResult = roundsCompleted > 0

  const stopLabel =
    stopReason === 'convergence_reached' ? '已收敛' :
    stopReason === 'max_rounds_reached'  ? `${roundsCompleted} 轮完成` :
    stopReason === 'oscillation_detected' ? '震荡停止' :
    null

  return (
    <div className="command-shell">
      {promptMascot}
      <section className="command">

        {/* ── Status bar (after first run) ─────────────────────────── */}
        {hasResult && (
          <div className="cmd-timeline">
            <span className="cmd-round-label">已完成 {roundsCompleted} 轮深推演</span>
            {stopLabel && (
              <span className="cmd-quality cmd-quality--complete">{stopLabel}</span>
            )}
          </div>
        )}

        {/* ── Input zone ───────────────────────────────────────────── */}
        <div className="cmd-body">

          {/* Left: context info */}
          <div className="cmd-context">
            <p className="cmd-context-label">分析对象</p>
            <div className="cmd-chips">
              <span className="cmd-chip cmd-chip--agents">
                <span className="cmd-chip-dot" />
                4 模块分析
              </span>
              <span className="cmd-chip cmd-chip--events">
                <span className="cmd-chip-dot" />
                多轮收敛
              </span>
            </div>
            {!hasResult && (
              <span className="cmd-context-empty">输入公司名称开始深推演</span>
            )}
            {hasResult && (
              <span className="cmd-context-empty">修改公司名称可重新推演</span>
            )}
          </div>

          {/* Right: input + submit */}
          <div className="cmd-input">
            <textarea
              value={draft}
              onChange={(e) => onDraftChange(e.target.value)}
              placeholder="输入公司名称，Enter 开始推演"
              rows={1}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                  e.preventDefault()
                  onSubmit()
                }
              }}
            />
            <div className="cmd-actions">
              <button
                className="run-btn"
                type="button"
                onClick={onSubmit}
                disabled={isRunning || !draft.trim()}
              >
                {isRunning ? '推演中…' : '▶ 开始推演'}
              </button>
            </div>
          </div>
        </div>

        {error && <p className="command-error">{error}</p>}
      </section>
    </div>
  )
}
