import type { ButtonHTMLAttributes, ReactNode } from 'react'

type Props = ButtonHTMLAttributes<HTMLButtonElement> & {
  children: ReactNode
}

export function IconButton({ children, className = '', ...props }: Props) {
  return (
    <button className={`icon-btn ${className}`.trim()} {...props}>
      {children}
    </button>
  )
}
