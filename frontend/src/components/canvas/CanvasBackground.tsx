import type { CSSProperties } from 'react'

export function CanvasBackground() {
  const topologyNodes = [
    { id: 'north', x: '18%', y: '16%', delay: '0s', scale: 1 },
    { id: 'east', x: '82%', y: '24%', delay: '1.2s', scale: 0.88 },
    { id: 'south', x: '72%', y: '78%', delay: '0.8s', scale: 1.06 },
    { id: 'west', x: '24%', y: '70%', delay: '1.6s', scale: 0.92 },
    { id: 'inner-1', x: '43%', y: '30%', delay: '0.4s', scale: 0.72 },
    { id: 'inner-2', x: '62%', y: '36%', delay: '1.8s', scale: 0.76 },
  ]

  return (
    <div className="canvas-background" aria-hidden="true">
      <div className="canvas-background__grid canvas-background__grid--primary" />
      <div className="canvas-background__grid canvas-background__grid--secondary" />
      <div className="canvas-background__glow canvas-background__glow--primary" />
      <div className="canvas-background__glow canvas-background__glow--secondary" />
      <div className="canvas-background__ring canvas-background__ring--inner" />
      <div className="canvas-background__ring canvas-background__ring--outer" />
      <div className="canvas-background__trace canvas-background__trace--north" />
      <div className="canvas-background__trace canvas-background__trace--south" />
      <div className="canvas-background__trace canvas-background__trace--cross" />
      {topologyNodes.map((node) => (
        <div
          key={node.id}
          className="canvas-background__node"
          style={{
            left: node.x,
            top: node.y,
            ['--node-scale']: node.scale,
            ['--node-delay']: node.delay,
          } as CSSProperties}
        >
          <span className="canvas-background__node-core" />
        </div>
      ))}
    </div>
  )
}
