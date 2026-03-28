export function BallSassy({ className = '' }: { className?: string }) {
  return (
    <svg
      className={`orb-svg ${className}`}
      viewBox="0 0 230 230"
      xmlns="http://www.w3.org/2000/svg"
      aria-hidden="true"
    >
      <defs>
        <radialGradient id="pyta-bg-happy" cx="36%" cy="33%" r="64%" fx="28%" fy="25%">
          <stop offset="0%"   stopColor="#A8C8F0"/>
          <stop offset="14%"  stopColor="#7AAAE8"/>
          <stop offset="35%"  stopColor="#4E7ED8"/>
          <stop offset="62%"  stopColor="#3968C8"/>
          <stop offset="88%"  stopColor="#2850A8"/>
          <stop offset="100%" stopColor="#1E3E8C"/>
        </radialGradient>
        <radialGradient id="pyta-hl-happy" cx="32%" cy="28%" r="42%">
          <stop offset="0%"   stopColor="#CCDFF8" stopOpacity="0.7"/>
          <stop offset="55%"  stopColor="#90B8E8" stopOpacity="0.18"/>
          <stop offset="100%" stopColor="#4E7ED8"  stopOpacity="0"/>
        </radialGradient>
      </defs>

      {/* Ball body */}
      <path fill="url(#pyta-bg-happy)"
        d="M115 12 C172 12,218 58,218 115 C218 172,172 218,115 218 C58 218,12 172,12 115 C12 58,58 12,115 12 Z"/>
      <path fill="url(#pyta-hl-happy)"
        d="M115 12 C172 12,218 58,218 115 C218 172,172 218,115 218 C58 218,12 172,12 115 C12 58,58 12,115 12 Z"/>

      {/* HAPPY idle face — ^ eyes + W mouth */}
      <g id="happy-idle">
        {/* Left eye */}
        <rect x="61"  y="84"  width="8"  height="2" fill="white"/>
        <rect x="61"  y="86"  width="9"  height="1" fill="white"/>
        <rect x="58"  y="87"  width="14" height="2" fill="white"/>
        <rect x="58"  y="89"  width="15" height="1" fill="white"/>
        <rect x="55"  y="90"  width="20" height="2" fill="white"/>
        <rect x="55"  y="92"  width="9"  height="1" fill="white"/>
        <rect x="67"  y="92"  width="9"  height="1" fill="white"/>
        <rect x="53"  y="93"  width="11" height="1" fill="white"/>
        <rect x="67"  y="93"  width="11" height="2" fill="white"/>
        <rect x="52"  y="94"  width="12" height="1" fill="white"/>
        <rect x="50"  y="95"  width="11" height="3" fill="white"/>
        <rect x="70"  y="95"  width="11" height="3" fill="white"/>
        <rect x="47"  y="98"  width="11" height="3" fill="white"/>
        <rect x="73"  y="98"  width="10" height="1" fill="white"/>
        <rect x="73"  y="99"  width="11" height="2" fill="white"/>
        <rect x="47"  y="101" width="8"  height="5" fill="white"/>
        <rect x="75"  y="101" width="9"  height="1" fill="white"/>
        <rect x="76"  y="102" width="8"  height="4" fill="white"/>
        {/* Right eye */}
        <rect x="147" y="84"  width="8"  height="2" fill="white"/>
        <rect x="147" y="86"  width="9"  height="1" fill="white"/>
        <rect x="144" y="87"  width="14" height="2" fill="white"/>
        <rect x="144" y="89"  width="15" height="1" fill="white"/>
        <rect x="141" y="90"  width="20" height="2" fill="white"/>
        <rect x="140" y="92"  width="10" height="1" fill="white"/>
        <rect x="153" y="92"  width="9"  height="1" fill="white"/>
        <rect x="139" y="93"  width="11" height="2" fill="white"/>
        <rect x="153" y="93"  width="11" height="2" fill="white"/>
        <rect x="135" y="95"  width="11" height="1" fill="white"/>
        <rect x="156" y="95"  width="11" height="1" fill="white"/>
        <rect x="135" y="96"  width="12" height="2" fill="white"/>
        <rect x="156" y="96"  width="12" height="1" fill="white"/>
        <rect x="156" y="97"  width="13" height="1" fill="white"/>
        <rect x="133" y="98"  width="11" height="3" fill="white"/>
        <rect x="159" y="98"  width="11" height="3" fill="white"/>
        <rect x="133" y="101" width="8"  height="5" fill="white"/>
        <rect x="161" y="101" width="9"  height="5" fill="white"/>
        {/* W mouth */}
        <rect x="78"  y="143" width="6"  height="6" fill="white"/>
        <rect x="104" y="143" width="6"  height="3" fill="white"/>
        <rect x="133" y="143" width="5"  height="6" fill="white"/>
        <rect x="101" y="146" width="11" height="2" fill="white"/>
        <rect x="101" y="148" width="12" height="1" fill="white"/>
        <rect x="78"  y="149" width="9"  height="2" fill="white"/>
        <rect x="99"  y="149" width="16" height="1" fill="white"/>
        <rect x="130" y="149" width="8"  height="2" fill="white"/>
        <rect x="98"  y="150" width="17" height="1" fill="white"/>
        <rect x="81"  y="151" width="7"  height="1" fill="white"/>
        <rect x="96"  y="151" width="8"  height="3" fill="white"/>
        <rect x="110" y="151" width="6"  height="1" fill="white"/>
        <rect x="127" y="151" width="9"  height="1" fill="white"/>
        <rect x="81"  y="152" width="8"  height="2" fill="white"/>
        <rect x="110" y="152" width="8"  height="2" fill="white"/>
        <rect x="127" y="152" width="8"  height="2" fill="white"/>
        <rect x="84"  y="154" width="17" height="3" fill="white"/>
        <rect x="113" y="154" width="20" height="1" fill="white"/>
        <rect x="113" y="155" width="19" height="2" fill="white"/>
        <rect x="87"  y="157" width="11" height="3" fill="white"/>
        <rect x="116" y="157" width="14" height="2" fill="white"/>
        <rect x="116" y="159" width="13" height="1" fill="white"/>
      </g>
    </svg>
  )
}
