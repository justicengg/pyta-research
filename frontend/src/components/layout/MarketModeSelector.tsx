import type { MarketMode } from '../../lib/types/canvas'

type Props = {
  onSelect: (mode: MarketMode) => void
}

export function MarketModeSelector({ onSelect }: Props) {
  return (
    <div className="mode-selector">
      <div className="mode-selector__inner">
        <div className="mode-selector__header">
          <h1 className="mode-selector__title">PYTA Research</h1>
          <p className="mode-selector__sub">选择分析模式开始研究</p>
        </div>

        <div className="mode-selector__cards">
          {/* 二级市场 */}
          <button
            className="mode-card mode-card--secondary"
            onClick={() => onSelect('secondary')}
          >
            <h2 className="mode-card__title">二级市场研究</h2>
            <p className="mode-card__desc">
              多参与者并行视角 · 快速市场解读
            </p>
            <ul className="mode-card__dims">
              <li>传统机构 · 量化 · 散户 · 海外资金 · 游资</li>
              <li>博弈解析层 · Interaction Resolution</li>
              <li>市场解读报告</li>
            </ul>
            <div className="mode-card__cta">进入分析 →</div>
          </button>

          {/* 一级市场 */}
          <button
            className="mode-card mode-card--primary"
            onClick={() => onSelect('primary')}
          >
            <h2 className="mode-card__title">一级市场研究</h2>
            <p className="mode-card__desc">
              深推演模式 · 多轮收敛 · 路径分叉
            </p>
            <ul className="mode-card__dims">
              <li>不确定性地图（6 维）</li>
              <li>创始人分析（四层结构）</li>
              <li>关键假设 · PathFork</li>
              <li>财务透视</li>
            </ul>
            <div className="mode-card__cta">进入分析 →</div>
          </button>
        </div>
      </div>
    </div>
  )
}
