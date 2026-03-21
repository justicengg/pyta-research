type Props = {
  draft: string
  onDraftChange: (value: string) => void
  onSubmit: () => void
  isRunning: boolean
  error: string | null
}

export function CommandConsole({ draft, onDraftChange, onSubmit, isRunning, error }: Props) {
  return (
    <section className="command">
      <div className="command-box">
        <textarea
          value={draft}
          onChange={(event) => onDraftChange(event.target.value)}
          placeholder="输入你的下一步操作，回车运行，Shift + Enter 换行。"
        />
        <div className="composer-tools">
          <div className="plus-wrap">
            <button className="plus-btn" aria-label="打开功能菜单" type="button">+</button>
          </div>
          <select className="mode-select" aria-label="模式切换" defaultValue="极简模式">
            <option>极简模式</option>
            <option>专家模式</option>
          </select>
          <button className="run-btn" type="button" onClick={onSubmit} disabled={isRunning || !draft.trim()}>
            {isRunning ? '运行中...' : '运行推演'}
          </button>
        </div>
        {error ? <p className="command-error">{error}</p> : null}
      </div>
    </section>
  )
}
