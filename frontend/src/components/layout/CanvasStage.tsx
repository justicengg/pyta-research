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
      <div className="stage-head">
        <div>
          <div className="eyebrow">融合方向</div>
          <h2>多 Agent 沙盘推演</h2>
          <p>核心场景在中心，多个市场参与者 Agent 围绕其运转。最近动作最清晰，历史步骤逐渐淡化，最终只把收敛结果送去画布中的结果卡位。</p>
        </div>
        <div className="chip-row">
          <span className={`chip ${isRunning ? 'chip-running' : ''}`}>{isRunning ? '运行中' : '就绪'}</span>
          <span className="chip quality-chip">{qualityLabel}</span>
        </div>
      </div>

      <div className="stage">
        <div className="canvas-layer">
          <CanvasBackground />
          <CanvasToolbar />

          <div className="center-core">
            <h3>腾讯 / 港股科技</h3>
            <p>当前推演对象仍然放在舞台中心。所有 Agent 围绕这个核心对象提供反应、解释、修正和收敛。</p>
            <div className="center-tags">
              <span className="core-tag">核心场景</span>
              <span className="core-tag">3 个月</span>
              <span className="core-tag">持续推演</span>
            </div>
          </div>

          {state.agents.map((agent) => (
            <AgentNode key={agent.id} agent={agent} />
          ))}

          <div className="ghost-node faded hint-card hint-news">
            新闻事件
            <small>腾讯合作扩张改善海外分发预期</small>
          </div>
          <div className="ghost-node hint-card hint-institution">
            机构判断
            <small>传统机构更重长期赔率，但不会忽视当前估值约束</small>
          </div>
          <div className="ghost-node active hint-card hint-active">
            当前活跃步骤
            <small>游资与散户情绪正在放大最新事件流的短线方向感</small>
          </div>

          {error ? <div className="canvas-error">{error}</div> : null}
        </div>
        <EventChips onSelect={(title) => onDraftChange(title)} />
        <CommandConsole
          draft={draft}
          onDraftChange={onDraftChange}
          onSubmit={onSubmit}
          isRunning={isRunning}
          error={error}
        />
      </div>

      <div className="stage-footer">这版前端共同基地工程先把结构、节点和结果卡位搭起来。现在底部控制台已经可以触发真实 secondary-market sandbox run，并把结果回写到节点与左侧信息流。</div>
    </section>
  )
}
