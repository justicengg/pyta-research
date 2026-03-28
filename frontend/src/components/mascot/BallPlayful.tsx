export function BallPlayful({ className = '' }: { className?: string }) {
  return (
    <svg
      className={`orb-svg ${className}`}
      viewBox="0 0 230 230"
      xmlns="http://www.w3.org/2000/svg"
      aria-hidden="true"
    >
      <defs>
        <radialGradient id="pyta-bg-smug" cx="36%" cy="33%" r="64%" fx="28%" fy="25%">
          <stop offset="0%"   stopColor="#A8C8F0"/>
          <stop offset="14%"  stopColor="#7AAAE8"/>
          <stop offset="35%"  stopColor="#4E7ED8"/>
          <stop offset="62%"  stopColor="#3968C8"/>
          <stop offset="88%"  stopColor="#2850A8"/>
          <stop offset="100%" stopColor="#1E3E8C"/>
        </radialGradient>
        <radialGradient id="pyta-hl-smug" cx="32%" cy="28%" r="42%">
          <stop offset="0%"   stopColor="#CCDFF8" stopOpacity="0.7"/>
          <stop offset="55%"  stopColor="#90B8E8" stopOpacity="0.18"/>
          <stop offset="100%" stopColor="#4E7ED8"  stopOpacity="0"/>
        </radialGradient>
      </defs>

      {/* Ball body */}
      <path fill="url(#pyta-bg-smug)"
        d="M115 12 C172 12,218 58,218 115 C218 172,172 218,115 218 C58 218,12 172,12 115 C12 58,58 12,115 12 Z"/>
      <path fill="url(#pyta-hl-smug)"
        d="M115 12 C172 12,218 58,218 115 C218 172,172 218,115 218 C58 218,12 172,12 115 C12 58,58 12,115 12 Z"/>

      {/* SMUG idle face — sunglasses + smirk */}
      <g id="smug-idle">
        {/* Left lens */}
        <rect x="40"  y="90"  width="46" height="5"  fill="white"/>
        <rect x="40"  y="95"  width="6"  height="11" fill="white"/>
        <rect x="60"  y="95"  width="26" height="9"  fill="white"/>
        <rect x="41"  y="101" width="8"  height="3"  fill="white"/>
        <rect x="58"  y="101" width="28" height="3"  fill="white"/>
        <rect x="41"  y="104" width="45" height="2"  fill="white"/>
        <rect x="46"  y="106" width="40" height="1"  fill="white"/>
        <rect x="46"  y="107" width="34" height="5"  fill="white"/>
        <rect x="52"  y="112" width="23" height="6"  fill="white"/>
        {/* Right lens */}
        <rect x="127" y="90"  width="45" height="5"  fill="white"/>
        <rect x="127" y="95"  width="5"  height="6"  fill="white"/>
        <rect x="147" y="95"  width="25" height="6"  fill="white"/>
        <rect x="127" y="101" width="8"  height="3"  fill="white"/>
        <rect x="144" y="101" width="28" height="3"  fill="white"/>
        <rect x="127" y="104" width="45" height="2"  fill="white"/>
        <rect x="131" y="106" width="36" height="1"  fill="white"/>
        <rect x="168" y="106" width="4"  height="1"  fill="white"/>
        <rect x="132" y="107" width="34" height="5"  fill="white"/>
        <rect x="138" y="112" width="23" height="6"  fill="white"/>
        {/* Smirk mouth */}
        <rect x="132" y="145" width="6"  height="3"  fill="white"/>
        <rect x="129" y="148" width="9"  height="2"  fill="white"/>
        <rect x="127" y="150" width="8"  height="2"  fill="white"/>
        <rect x="123" y="153" width="9"  height="1"  fill="white"/>
        <rect x="121" y="154" width="11" height="2"  fill="white"/>
        <rect x="81"  y="156" width="48" height="3"  fill="white"/>
        <rect x="81"  y="159" width="45" height="3"  fill="white"/>
      </g>
    </svg>
  )
}
