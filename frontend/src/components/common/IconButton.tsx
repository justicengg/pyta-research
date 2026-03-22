import { forwardRef } from 'react'
import type { ButtonHTMLAttributes, ReactNode } from 'react'

type Props = ButtonHTMLAttributes<HTMLButtonElement> & {
  children: ReactNode
}

export const IconButton = forwardRef<HTMLButtonElement, Props>(
  ({ children, className = '', ...props }, ref) => (
    <button ref={ref} className={`icon-btn ${className}`.trim()} {...props}>
      {children}
    </button>
  )
)
