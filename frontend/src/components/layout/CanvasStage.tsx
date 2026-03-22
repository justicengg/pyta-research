import type { CanvasState } from '../../lib/types/canvas'
import { AgentNode } from '../canvas/AgentNode'
import { CanvasBackground } from '../canvas/CanvasBackground'
import { CanvasToolbar } from '../canvas/CanvasToolbar'
import { EventChips } from '../canvas/EventChips'
import { CommandConsole } from './CommandConsole'

type Props = {
  state: CanvasState
  draft: string
  onDraftChange: (value: string) => void
  onSubmit: () => void
  isRunning: boolean
  error: string | null
  qualityLabel: string
}

export function CanvasStage({
  state,
  draft,
  onDraftChange,
  onSubmit,
  isRunning,
  error,
  qualityLabel,
}: Props) {
  return (
    <section className="stage-wrap">

      {/* Zone A — Context bar */}
      <div className="stage-head">
        <div className="stage-head-left">
          <div className="eyebrow">融合方向</div>
          <h2>多 Agent 沙盘推演</h2>
        </div>
        <div className="chip-row">
          <span className={`chip ${isRunning ? 'chip-running' : ''}`}>
            {isRunning ? '运行中' : '就绪'}
          </span>
          <span className="chip quality-chip">{qualityLabel}</span>
        </div>
      </div>

      {/* Zone B — Canvas viewport */}
      <div className="stage">
        <div className="canvas-layer">
          <CanvasBackground />

          {/* Floating draggable toolbar */}
          <CanvasToolbar
            onRun={onSubmit}
            isRunning={isRunning}
            onSceneSettings={() => {/* TODO: open scene settings modal */}}
          />

          {/* Center core */}
          <div className="center-core">
            <h3>腾讯 / 港股科技</h3>
            <p>核心推演对象。所有 Agent 围绕这个核心对象提供反应、解释、修正和收敛。</p>
            <div className="center-tags">
              <span className="core-tag">核心场景</span>
              <span className="core-tag">3 个月</span>
              <span className="core-tag">持续推演</span>
            </div>
          </div>

          {/* Agent nodes */}
          {state.agents.map((agent) => (
            <AgentNode key={agent.id} agent={agent} />
          ))}

          {error ? <div className="canvas-error">{error}</div> : null}
        </div>

        {/* Event chips — 在 canvas-layer 之外，不被遮挡 */}
        <EventChips onSelect={(title) => onDraftChange(title)} />
      </div>

      {/* Zone C — Command console */}
      <CommandConsole
        draft={draft}
        onDraftChange={onDraftChange}
        onSubmit={onSubmit}
        isRunning={isRunning}
        error={error}
      />
    </section>
  )
}
