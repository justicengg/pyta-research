import type { OrbMode, OrbTrigger, OrbVariant } from '../../lib/orb/promptProfiles'

type Props = {
  visible: boolean
  message: string
  variant: OrbVariant
  mode: OrbMode
  trigger: OrbTrigger
}

export function PromptMascot({ visible, message, variant, mode, trigger }: Props) {
  if (mode === 'off') {
    return null
  }

  return (
    <div
      className={`prompt-mascot prompt-mascot--${variant} prompt-mascot--${mode} prompt-mascot--${trigger}${visible ? ' prompt-mascot--visible' : ''}`}
      aria-hidden={!visible}
    >
      <div className="prompt-mascot-bubble">
        <span>{message}</span>
      </div>
      <div className="prompt-mascot-pair" aria-hidden="true">
        <div className="prompt-mascot-orb prompt-mascot-orb--playful" />
        {mode === 'full' ? <div className="prompt-mascot-orb prompt-mascot-orb--tsundere" /> : null}
      </div>
    </div>
  )
}
