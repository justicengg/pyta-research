import { IconButton } from '../common/IconButton'
import type { CanvasState } from '../../lib/types/canvas'
import type { CanvasInputEvent, SandboxSessionStatus } from '../../lib/types/sandbox'

type Props = {
  collapsed: boolean
  onToggle: () => void
  state: CanvasState
  currentInputEvents: CanvasInputEvent[]
  sessionStatus: SandboxSessionStatus
  error: string | null
}

export function InformationPanel({ collapsed, onToggle, state, currentInputEvents, sessionStatus, error }: Props) {
  return (
    <aside className={`sidebar ${collapsed ? 'collapsed' : ''}`}>
      <div className="sidebar-head">
        <button className="collapse-dot left" onClick={onToggle} aria-label="展开左侧边栏" />
        <div>
          <div className="eyebrow">左侧边栏</div>
          <h2>信息层</h2>
        </div>
        <div className="head-actions">
          <IconButton aria-label="打开设置">⚙</IconButton>
          <IconButton onClick={onToggle} aria-label="收起左侧边栏">⟨</IconButton>
        </div>
      </div>
      <div className="side-search">
        <input type="text" defaultValue="搜索来源、事件、参考资料" />
      </div>
      <div className="sidebar-body">
        <section className="section">
          <div className="section-label">当前运行</div>
          <div className="stream-item current-run-card">
            <strong>{sessionStatus}</strong>
            <span>{error ?? (currentInputEvents.length ? `已提交 ${currentInputEvents.length} 条输入事件。` : '等待控制台提交。')}</span>
          </div>
        </section>

        <section className="section">
          <div className="section-label">当前输入事件</div>
          <div className="stream">
            {currentInputEvents.length > 0 ? (
              currentInputEvents.map((item) => (
                <div className="stream-item" key={item.eventId}>
                  <strong>{item.eventType}</strong>
                  <span>{item.content}</span>
                  <span className="stream-meta">{item.source} · {new Date(item.timestamp).toLocaleString('zh-CN')}</span>
                </div>
              ))
            ) : (
              <div className="stream-item stream-item-empty">
                <strong>暂无输入</strong>
                <span>在底部控制台提交一次推演指令后，这里会显示当前输入事件。</span>
              </div>
            )}
          </div>
        </section>

        <section className="section">
          <div className="section-label">外部 Agent</div>
          <div className="inline-entry">
            <div className="inline-entry-main">
              <span className="inline-entry-title">外部 Agent 接入口</span>
              <span className="inline-entry-sub">后续支持用户自定义 Agent 与内置 Agent 协作接入</span>
            </div>
            <span className="status-pill warning">预留</span>
          </div>
        </section>

        <section className="section">
          <div className="section-label">已接入数据</div>
          {state.leftPanel.connectedSources.map((item) => (
            <div className="ghost-node static-card" key={item.title}>
              {item.title}
              <small>{item.description}</small>
            </div>
          ))}
        </section>

        <section className="section">
          <div className="section-label">实时信息流</div>
          <div className="stream">
            {state.leftPanel.liveEvents.map((item) => (
              <div className="stream-item" key={item.title}>
                <strong>{item.title}</strong>
                <span>{item.description}</span>
              </div>
            ))}
          </div>
        </section>

        <section className="section">
          <div className="section-label">推荐信息流</div>
          <div className="stream">
            {state.leftPanel.recommendedFeeds.map((item) => (
              <div className="stream-item" key={item.title}>
                <strong>{item.title}</strong>
                <span>{item.description}</span>
              </div>
            ))}
          </div>
        </section>
      </div>
      <div className="sidebar-footer">左侧信息层只负责输入上下文：已接入数据、实时信息流、推荐信息流。安全配置继续留在齿轮设置里，不出现在第一层。</div>
    </aside>
  )
}
