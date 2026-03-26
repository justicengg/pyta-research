export type OrbVariant = 'traditional' | 'product_logic' | 'ai_native'
export type OrbMode = 'full' | 'soft' | 'off'
export type OrbTrigger = 'first_load' | 'first_complete' | 'idle_nudge'

type OrbProfile = {
  dwellMs: number
  idleDelayMs: number
  copy: Record<OrbTrigger, string[]>
}

export const DEFAULT_ORB_VARIANT: OrbVariant = 'product_logic'
export const DEFAULT_ORB_MODE: OrbMode = 'full'

export const ORB_PROFILES: Record<OrbVariant, OrbProfile> = {
  traditional: {
    dwellMs: 8000,
    idleDelayMs: 10000,
    copy: {
      first_load: ['先从一个具体事件开始', '给我一个清晰的问题'],
      first_complete: ['先收一轮，再决定深挖方向', '结果出来了，挑一条线继续'],
      idle_nudge: ['需要时，先抛一个事件', '从一个信号开始就够了'],
    },
  },
  product_logic: {
    dwellMs: 8000,
    idleDelayMs: 8000,
    copy: {
      first_load: ['说吧，今天研究什么', '先给我一个具体事件'],
      first_complete: ['结果出来了，要继续追哪条线？', '先收一轮，再决定往哪边深挖'],
      idle_nudge: ['从一个信号开始就够了', '先抛一个事件，我们来推一轮'],
    },
  },
  ai_native: {
    dwellMs: 8000,
    idleDelayMs: 9000,
    copy: {
      first_load: ['我在，先给我一个起点', '把问题抛进来，我来接住'],
      first_complete: ['这一轮有结果了，我想继续校验一下', '结果已回传，要不要追它的分歧点'],
      idle_nudge: ['我还在线，给我一个新的研究信号', '如果卡住了，先丢一个事件过来'],
    },
  },
}

export function resolveOrbVariant(): OrbVariant {
  if (typeof window === 'undefined') return DEFAULT_ORB_VARIANT
  const search = new URLSearchParams(window.location.search)
  const queryValue = search.get('orbVariant')
  const storedValue = window.localStorage.getItem('pyta.orbVariant')
  const candidate = (queryValue || storedValue || DEFAULT_ORB_VARIANT) as OrbVariant
  return candidate in ORB_PROFILES ? candidate : DEFAULT_ORB_VARIANT
}

export function resolveOrbMode(): OrbMode {
  if (typeof window === 'undefined') return DEFAULT_ORB_MODE
  const search = new URLSearchParams(window.location.search)
  const queryValue = search.get('orbMode')
  const storedValue = window.localStorage.getItem('pyta.orbMode')
  const candidate = (queryValue || storedValue || DEFAULT_ORB_MODE) as OrbMode
  return candidate === 'soft' || candidate === 'off' || candidate === 'full'
    ? candidate
    : DEFAULT_ORB_MODE
}

export function pickOrbMessage(variant: OrbVariant, trigger: OrbTrigger): string {
  const options = ORB_PROFILES[variant].copy[trigger]
  return options[Math.floor(Math.random() * options.length)] ?? options[0] ?? ''
}
