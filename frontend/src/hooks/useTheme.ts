import { useEffect, useState } from 'react'

export type Theme = 'light' | 'dark' | 'auto'

function applyTheme(theme: Theme) {
  const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches
  const resolved = theme === 'auto' ? (prefersDark ? 'dark' : 'light') : theme
  document.documentElement.setAttribute('data-theme', resolved)
}

export function useTheme() {
  const [theme, setThemeState] = useState<Theme>(() => {
    return (localStorage.getItem('pyta-theme') as Theme) ?? 'auto'
  })

  useEffect(() => {
    applyTheme(theme)
    localStorage.setItem('pyta-theme', theme)

    if (theme === 'auto') {
      const mq = window.matchMedia('(prefers-color-scheme: dark)')
      const handler = () => applyTheme('auto')
      mq.addEventListener('change', handler)
      return () => mq.removeEventListener('change', handler)
    }
  }, [theme])

  function setTheme(t: Theme) {
    setThemeState(t)
  }

  return { theme, setTheme }
}
