import { useEffect, useRef, useState } from 'react'
import { IconButton } from '../common/IconButton'
import { SettingsPopover } from './SettingsPopover'
import { AddSourceModal } from './AddSourceModal'
import { useTheme } from '../../hooks/useTheme'
import { fetchConnectors, deleteConnector, type ConnectorResponse } from '../../lib/api/sources'
import type { CanvasState, RecommendedBundle } from '../../lib/types/canvas'
import type { CanvasInputEvent, SandboxSessionStatus } from '../../lib/types/sandbox'

type Props = {
  collapsed: boolean
  onToggle: () => void
  state: CanvasState
  currentInputEvents: CanvasInputEvent[]
  sessionStatus: SandboxSessionStatus
  error: string | null
}

function ConnectorStatusDot({ status }: { status: ConnectorResponse['status'] }) {
  const colorMap: Record<string, string> = {
    healthy: 'var(--accent)',
    syncing: 'var(--orange)',
    error: '#c44949',
    inactive: 'var(--text-3)',
  }
  return (
    <span
      className="connector-status-dot"
      style={{ background: colorMap[status] ?? 'var(--text-3)' }}
      title={status}
    />
  )
}

function SourceCard({ source, onDelete }: { source: ConnectorResponse; onDelete: (id: string) => void }) {
  const [confirming, setConfirming] = useState(false)

  async function handleDelete() {
    if (!confirming) { setConfirming(true); return }
    await deleteConnector(source.id)
    onDelete(source.id)
  }

  return (
    <div className="connector-card">
      <div className="connector-card-head">
        <ConnectorStatusDot status={source.status} />
        <span className="connector-title">{source.title}</span>
        <span className="connector-cost">{source.cost}</span>
        <button
          className="connector-delete-btn"
          onClick={handleDelete}
          title={confirming ? '再次点击确认删除' : '移除此来源'}
        >
          {confirming ? '确认?' : '×'}
        </button>
      </div>
      <div className="connector-meta">
        <span className="connector-caps">{source.capabilities.join(' · ')}</span>
        <span className="connector-sync">
          {source.status === 'syncing' ? '同步中…' : source.last_synced_at ? source.last_synced_at : '—'}
        </span>
      </div>
    </div>
  )
}

function BundleRow({ bundle }: { bundle: RecommendedBundle }) {
  return (
    <div className="bundle-row">
      <div className="bundle-row-main">
        <span className="bundle-name">{bundle.name}</span>
        <span className="bundle-reason">{bundle.reason}</span>
      </div>
      <button className="bundle-add-btn" aria-label="接入此 Bundle">+</button>
    </div>
  )
}

export function InformationPanel({ collapsed, onToggle, state, currentInputEvents, sessionStatus, error }: Props) {
  const { theme, setTheme } = useTheme()
  const [settingsOpen, setSettingsOpen] = useState(false)
  const [addSourceOpen, setAddSourceOpen] = useState(false)
  const [liveConnectors, setLiveConnectors] = useState<ConnectorResponse[]>([])
  const gearRef = useRef<HTMLButtonElement>(null)

  useEffect(() => {
    fetchConnectors().then(setLiveConnectors).catch(console.error)
  }, [])

  function handleConnectorCreated(c: ConnectorResponse) {
    setLiveConnectors((prev) => [c, ...prev])
    setAddSourceOpen(false)
  }

  function handleConnectorDeleted(id: string) {
    setLiveConnectors((prev) => prev.filter((c) => c.id !== id))
  }

  if (collapsed) {
    return (
      <aside className="sidebar collapsed">
        <button
          ref={gearRef}
          className="sidebar-float-btn"
          onClick={() => setSettingsOpen((v) => !v)}
          aria-label="打开设置"
        >
          ⚙
        </button>
        {settingsOpen && (
          <SettingsPopover
            theme={theme}
            setTheme={setTheme}
            onClose={() => setSettingsOpen(false)}
            anchorRef={gearRef}
          />
        )}
        <button className="sidebar-float-btn" onClick={onToggle} aria-label="展开左侧边栏">
          ⟩
        </button>
      </aside>
    )
  }

  return (
    <aside className="sidebar">
      <div className="sidebar-head">
        <div>
          <div className="eyebrow">Layer 1</div>
          <h2>信息层</h2>
        </div>
        <div className="head-actions">
          <div style={{ position: 'relative' }}>
            <IconButton
              ref={gearRef}
              aria-label="打开设置"
              onClick={() => setSettingsOpen((v) => !v)}
            >⚙</IconButton>
            {settingsOpen && (
              <SettingsPopover
                theme={theme}
                setTheme={setTheme}
                onClose={() => setSettingsOpen(false)}
                anchorRef={gearRef}
              />
            )}
          </div>
          <IconButton onClick={onToggle} aria-label="收起左侧边栏">⟨</IconButton>
        </div>
      </div>

      <div className="side-search">
        <input type="text" placeholder="搜索来源、事件、参考资料" />
      </div>

      <div className="sidebar-body">

        {/* SOURCES */}
        <section className="section">
          <div className="section-label-row">
            <span className="section-label">Sources</span>
            <button
              className="section-action-btn"
              aria-label="接入新来源"
              onClick={() => setAddSourceOpen(true)}
            >
              + 接入
            </button>
          </div>
          {liveConnectors.length === 0 && (
            <p className="section-empty">暂无接入来源，点击「+ 接入」添加数据源。</p>
          )}
          {liveConnectors.map((source) => (
            <SourceCard key={source.id} source={source} onDelete={handleConnectorDeleted} />
          ))}
        </section>

        {addSourceOpen && (
          <AddSourceModal
            onClose={() => setAddSourceOpen(false)}
            onCreated={handleConnectorCreated}
          />
        )}

        {/* RECOMMENDED */}
        <section className="section">
          <div className="section-label">Recommended</div>
          {state.leftPanel.recommendedBundles.map((bundle) => (
            <BundleRow key={bundle.name} bundle={bundle} />
          ))}
        </section>

        {/* SESSION */}
        <section className="section">
          <div className="section-label">Session</div>
          <div className="session-row">
            <span className={`session-status-dot ${sessionStatus === 'running' ? 'running' : ''}`} />
            <span className="session-status-text">
              {error ?? (sessionStatus === 'running' ? '推演运行中' : sessionStatus)}
            </span>
            {currentInputEvents.length > 0 && (
              <span className="session-event-count">{currentInputEvents.length} 条输入</span>
            )}
          </div>
        </section>

        {/* EXTERNAL AGENT */}
        <section className="section">
          <div className="section-label">External Agent</div>
          <div className="inline-entry">
            <div className="inline-entry-main">
              <span className="inline-entry-title">外部 Agent 接入口</span>
              <span className="inline-entry-sub">后续支持用户自定义 Agent 与内置 Agent 协作接入</span>
            </div>
            <span className="status-pill warning">预留</span>
          </div>
        </section>

      </div>
    </aside>
  )
}
