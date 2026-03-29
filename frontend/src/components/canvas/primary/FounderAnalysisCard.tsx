import type { FounderAnalysisData } from '../../../lib/types/primaryCanvas'
import {
  ARCHETYPE_LABELS,
  STAGE_FIT_LABELS,
  STAGE_LABELS,
} from '../../../lib/types/primaryCanvas'

type Props = {
  data: FounderAnalysisData
  position: { x: number; y: number }
  onDragMove: (dx: number, dy: number) => void
}

const SCORE_LABEL: Record<string, string> = { high: '高', medium: '中', low: '低' }

export function FounderAnalysisCard({ data, position, onDragMove }: Props) {
  const dragRef = { active: false, lastX: 0, lastY: 0 }

  function handlePointerDown(e: React.PointerEvent<HTMLDivElement>) {
    if (e.button !== 0) return
    const target = e.target as HTMLElement
    if (target.closest('button, input, textarea, select, a')) return
    e.stopPropagation()
    e.currentTarget.setPointerCapture(e.pointerId)
    dragRef.active = true
    dragRef.lastX = e.clientX
    dragRef.lastY = e.clientY
  }

  function handlePointerMove(e: React.PointerEvent<HTMLDivElement>) {
    if (!dragRef.active) return
    const dx = e.clientX - dragRef.lastX
    const dy = e.clientY - dragRef.lastY
    dragRef.lastX = e.clientX
    dragRef.lastY = e.clientY
    onDragMove(dx, dy)
  }

  function handlePointerUp() { dragRef.active = false }

  return (
    <div
      className="pm-card pm-card--founder"
      style={{ left: position.x, top: position.y }}
      data-no-pan
      onPointerDown={handlePointerDown}
      onPointerMove={handlePointerMove}
      onPointerUp={handlePointerUp}
      onPointerCancel={handlePointerUp}
    >
      <div className="pm-card__header">
        <span className="pm-card__label">模块 2</span>
        <h3 className="pm-card__title">创始人分析</h3>
      </div>

      <div className="pm-card__body">
        {/* 阶段 + 原型 + 匹配度 */}
        <div className="pm-founder-meta">
          <div className="pm-founder-meta-item">
            <span className="pm-founder-meta-key">公司阶段</span>
            <span className="pm-founder-meta-val">{STAGE_LABELS[data.companyStage]}</span>
          </div>
          <div className="pm-founder-meta-item">
            <span className="pm-founder-meta-key">创始人原型</span>
            <span className="pm-founder-meta-val">{ARCHETYPE_LABELS[data.archetype]}</span>
          </div>
          <div className="pm-founder-meta-item">
            <span className="pm-founder-meta-key">阶段匹配</span>
            <span className={`pm-founder-fit pm-founder-fit--${data.stageFit}`}>
              {STAGE_FIT_LABELS[data.stageFit]}
            </span>
          </div>
        </div>

        {/* 固定维度评分 */}
        <div className="pm-founder-scores">
          {[
            { key: 'Founder-Market Fit', val: SCORE_LABEL[data.founderMarketFit] },
            { key: '团队构建能力',        val: SCORE_LABEL[data.teamBuilding] },
            { key: '自我认知',            val: SCORE_LABEL[data.selfAwareness] },
          ].map(({ key, val }) => (
            <div key={key} className="pm-uncertainty-row">
              <span className="pm-uncertainty-dim">{key}</span>
              <span className="pm-uncertainty-score pm-uncertainty-score--medium">{val}</span>
            </div>
          ))}
        </div>

        {/* 阶段匹配叙述 */}
        {data.stageFitNarrative && (
          <p className="pm-card__narrative">{data.stageFitNarrative}</p>
        )}

        {/* 关键风险 */}
        {data.keyRisks.length > 0 && (
          <ul className="pm-card__risks">
            {data.keyRisks.map((risk, i) => (
              <li key={i}>{risk}</li>
            ))}
          </ul>
        )}
      </div>
    </div>
  )
}
