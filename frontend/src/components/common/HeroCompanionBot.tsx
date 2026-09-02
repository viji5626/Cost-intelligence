import React, { useState, useEffect } from 'react';

export type BotEmotion = 'happy' | 'love' | 'surprised' | 'curious' | 'thinking';

interface HeroCompanionBotProps {
  emotion?: BotEmotion;
  size?: number;
  isHovered?: boolean;
  isLoading?: boolean;
  onClick?: () => void;
  showBody?: boolean;
}

export const HeroCompanionBot: React.FC<HeroCompanionBotProps> = ({
  emotion: controlledEmotion,
  size = 56,
  isHovered = false,
  isLoading = false,
  onClick,
  showBody = true,
}) => {
  const [internalEmotion, setInternalEmotion] = useState<BotEmotion>('happy');

  // Automatically cycle through cute emotions periodically when idle
  useEffect(() => {
    if (controlledEmotion) return;
    if (isLoading) {
      setInternalEmotion('thinking');
      return;
    }

    const emotionList: BotEmotion[] = ['happy', 'love', 'surprised', 'curious'];
    let idx = 0;

    const interval = setInterval(() => {
      idx = (idx + 1) % emotionList.length;
      setInternalEmotion(emotionList[idx]);
    }, 4000);

    return () => clearInterval(interval);
  }, [controlledEmotion, isLoading]);

  // When hovered, show happy or love
  const activeEmotion = controlledEmotion || (isLoading ? 'thinking' : (isHovered ? 'love' : internalEmotion));

  const renderVisorExpression = () => {
    switch (activeEmotion) {
      case 'love':
        return (
          <g className="bot-expression-love">
            {/* Left Heart Eye */}
            <path
              d="M 38 46 C 38 41, 30 38, 26 44 C 22 38, 14 41, 14 46 C 14 55, 26 62, 26 62 C 26 62, 38 55, 38 46 Z"
              fill="#FF1A4B"
              filter="url(#bot-red-glow)"
              className="bot-pulse-eye"
            />
            {/* Right Heart Eye */}
            <path
              d="M 66 46 C 66 41, 58 38, 54 44 C 50 38, 42 41, 42 46 C 42 55, 54 62, 54 62 C 54 62, 66 55, 66 46 Z"
              fill="#FF1A4B"
              filter="url(#bot-red-glow)"
              className="bot-pulse-eye"
            />
            {/* Cute Smile Mouth */}
            <path
              d="M 35 63 Q 40 68 45 63"
              fill="none"
              stroke="#FF1A4B"
              strokeWidth="2.5"
              strokeLinecap="round"
            />
          </g>
        );

      case 'surprised':
        return (
          <g className="bot-expression-surprised">
            {/* Left Big Round Eye */}
            <circle cx="27" cy="48" r="12" fill="#00F0FF" filter="url(#bot-cyan-glow)" />
            <circle cx="27" cy="48" r="8" fill="#0B132B" />
            <circle cx="30" cy="45" r="3.5" fill="#FFFFFF" />
            <circle cx="24" cy="51" r="1.5" fill="#FFFFFF" />

            {/* Right Big Round Eye */}
            <circle cx="53" cy="48" r="12" fill="#00F0FF" filter="url(#bot-cyan-glow)" />
            <circle cx="53" cy="48" r="8" fill="#0B132B" />
            <circle cx="56" cy="45" r="3.5" fill="#FFFFFF" />
            <circle cx="50" cy="51" r="1.5" fill="#FFFFFF" />

            {/* Open Happy 'D' Mouth */}
            <path
              d="M 36 60 Q 40 60 44 60 Q 44 67 40 67 Q 36 67 36 60 Z"
              fill="#00F0FF"
              filter="url(#bot-cyan-glow)"
            />
          </g>
        );

      case 'curious':
        return (
          <g className="bot-expression-curious">
            {/* Left Big Puppy Eye */}
            <ellipse cx="27" cy="49" rx="11" ry="13" fill="#00F0FF" filter="url(#bot-cyan-glow)" />
            <ellipse cx="27" cy="49" rx="7.5" ry="9.5" fill="#0A0E1A" />
            <circle cx="25" cy="45" r="4" fill="#FFFFFF" />
            <circle cx="29" cy="53" r="2" fill="#FFFFFF" />
            {/* Left Eyebrow Arch */}
            <path d="M 18 36 Q 27 31 36 37" fill="none" stroke="#00F0FF" strokeWidth="2" strokeLinecap="round" />

            {/* Right Big Puppy Eye */}
            <ellipse cx="53" cy="49" rx="11" ry="13" fill="#00F0FF" filter="url(#bot-cyan-glow)" />
            <ellipse cx="53" cy="49" rx="7.5" ry="9.5" fill="#0A0E1A" />
            <circle cx="51" cy="45" r="4" fill="#FFFFFF" />
            <circle cx="55" cy="53" r="2" fill="#FFFFFF" />
            {/* Right Eyebrow Arch */}
            <path d="M 44 37 Q 53 31 62 36" fill="none" stroke="#00F0FF" strokeWidth="2" strokeLinecap="round" />

            {/* Shy Wavy Mouth */}
            <path
              d="M 35 64 Q 38 62 40 64 Q 42 66 45 64"
              fill="none"
              stroke="#00F0FF"
              strokeWidth="2.5"
              strokeLinecap="round"
            />
          </g>
        );

      case 'thinking':
        return (
          <g className="bot-expression-thinking">
            {/* Scanning Eye Rings */}
            <circle cx="28" cy="48" r="9" fill="none" stroke="#00F0FF" strokeWidth="3" strokeDasharray="6 3" className="bot-spin-eye" />
            <circle cx="28" cy="48" r="3" fill="#00F0FF" filter="url(#bot-cyan-glow)" />

            <circle cx="52" cy="48" r="9" fill="none" stroke="#00F0FF" strokeWidth="3" strokeDasharray="6 3" className="bot-spin-eye" />
            <circle cx="52" cy="48" r="3" fill="#00F0FF" filter="url(#bot-cyan-glow)" />

            {/* Concentrating Flat Mouth */}
            <line x1="36" y1="63" x2="44" y2="63" stroke="#00F0FF" strokeWidth="2.5" strokeLinecap="round" />
          </g>
        );

      case 'happy':
      default:
        return (
          <g className="bot-expression-happy">
            {/* Left Happy Curved Eye Arch (^^) */}
            <path
              d="M 18 50 Q 28 35 38 50"
              fill="none"
              stroke="#00F0FF"
              strokeWidth="4"
              strokeLinecap="round"
              filter="url(#bot-cyan-glow)"
            />
            {/* Right Happy Curved Eye Arch (^^) */}
            <path
              d="M 42 50 Q 52 35 62 50"
              fill="none"
              stroke="#00F0FF"
              strokeWidth="4"
              strokeLinecap="round"
              filter="url(#bot-cyan-glow)"
            />
            {/* Happy Curved Smile Mouth */}
            <path
              d="M 34 61 Q 40 68 46 61"
              fill="none"
              stroke="#00F0FF"
              strokeWidth="2.8"
              strokeLinecap="round"
              filter="url(#bot-cyan-glow)"
            />
          </g>
        );
    }
  };

  return (
    <div
      onClick={onClick}
      className="hero-companion-bot-container"
      style={{
        width: `${size}px`,
        height: showBody ? `${size * 1.3}px` : `${size}px`,
        cursor: 'pointer',
        position: 'relative',
        display: 'inline-flex',
        alignItems: 'center',
        justifyContent: 'center',
        userSelect: 'none',
      }}
      title="Hero AI Companion • Click to Ask"
    >
      <svg
        viewBox="0 0 100 130"
        width="100%"
        height="100%"
        xmlns="http://www.w3.org/2000/svg"
        className="hero-bot-svg"
      >
        <defs>
          {/* 3D Glossy Yellow Head Gradients */}
          <radialGradient id="botYellowHead" cx="35%" cy="30%" r="70%">
            <stop offset="0%" stopColor="#FFF275" />
            <stop offset="25%" stopColor="#FFCC00" />
            <stop offset="70%" stopColor="#F59E0B" />
            <stop offset="100%" stopColor="#B45309" />
          </radialGradient>

          {/* 3D Torso Gradient */}
          <linearGradient id="botTorsoGrad" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor="#FFE033" />
            <stop offset="45%" stopColor="#F59E0B" />
            <stop offset="100%" stopColor="#92400E" />
          </linearGradient>

          {/* Glossy Black Visor Gradient */}
          <radialGradient id="botVisorGlass" cx="45%" cy="35%" r="65%">
            <stop offset="0%" stopColor="#1E293B" />
            <stop offset="60%" stopColor="#0B0F19" />
            <stop offset="100%" stopColor="#030712" />
          </radialGradient>

          {/* Cyan LED Glow Filter */}
          <filter id="bot-cyan-glow" x="-30%" y="-30%" width="160%" height="160%">
            <feGaussianBlur stdDeviation="2.5" result="blur" />
            <feComposite in="SourceGraphic" in2="blur" operator="over" />
          </filter>

          {/* Red Heart Glow Filter */}
          <filter id="bot-red-glow" x="-30%" y="-30%" width="160%" height="160%">
            <feGaussianBlur stdDeviation="3" result="blur" />
            <feComposite in="SourceGraphic" in2="blur" operator="over" />
          </filter>

          {/* 3D Head Drop Shadow */}
          <filter id="bot-head-shadow" x="-20%" y="-20%" width="140%" height="140%">
            <feDropShadow dx="0" dy="4" stdDeviation="3" floodColor="rgba(0,0,0,0.35)" />
          </filter>
        </defs>

        {showBody && (
          <g className="bot-body-group">
            {/* Unicycle Single Wheel (Lower Base) */}
            <ellipse cx="50" cy="118" rx="14" ry="7" fill="rgba(0,0,0,0.25)" />
            <circle cx="50" cy="115" r="10" fill="#1E293B" stroke="#0F172A" strokeWidth="2" />
            <circle cx="50" cy="115" r="6" fill="#F59E0B" />
            <circle cx="50" cy="115" r="2.5" fill="#0F172A" />

            {/* Wheel Strut / Leg */}
            <path d="M 45 96 L 46 112 A 4 4 0 0 0 54 112 L 55 96 Z" fill="url(#botTorsoGrad)" stroke="#B45309" strokeWidth="0.8" />

            {/* Robotic Torso */}
            <ellipse cx="50" cy="85" rx="16" ry="14" fill="url(#botTorsoGrad)" stroke="#B45309" strokeWidth="1" />
            {/* Torso Waist Band (Black Stripe) */}
            <path d="M 35 87 Q 50 93 65 87 Q 64 91 50 95 Q 36 91 35 87 Z" fill="#0F172A" />

            {/* Left Robotic Arm & Hand */}
            <g className="bot-left-arm">
              <path d="M 34 78 Q 22 84 18 96" fill="none" stroke="url(#botTorsoGrad)" strokeWidth="6" strokeLinecap="round" />
              <circle cx="18" cy="96" r="3.5" fill="#0F172A" />
              {/* Fingers */}
              <circle cx="15" cy="99" r="1.5" fill="#0F172A" />
              <circle cx="20" cy="100" r="1.5" fill="#0F172A" />
            </g>

            {/* Right Waving Robotic Arm */}
            <g className="bot-right-arm">
              <path d="M 66 78 Q 80 80 86 68" fill="none" stroke="url(#botTorsoGrad)" strokeWidth="6" strokeLinecap="round" />
              <circle cx="86" cy="68" r="3.5" fill="#0F172A" />
              {/* Waving Hand Palm & Fingers */}
              <circle cx="88" cy="64" r="1.8" fill="#0F172A" />
              <circle cx="91" cy="67" r="1.8" fill="#0F172A" />
              <circle cx="89" cy="71" r="1.8" fill="#0F172A" />
            </g>

            {/* Neck Joint Connector */}
            <rect x="46" y="68" width="8" height="6" rx="2" fill="#0F172A" />
          </g>
        )}

        {/* 3D Glossy Yellow Robot Head */}
        <g className="bot-head-group" filter="url(#bot-head-shadow)">
          {/* Left Headphone Ear Pod */}
          <ellipse cx="14" cy="48" rx="5" ry="12" fill="#D97706" />
          <ellipse cx="12" cy="48" rx="4" ry="9" fill="#0F172A" stroke="#FFCC00" strokeWidth="1" />

          {/* Right Headphone Ear Pod */}
          <ellipse cx="86" cy="48" rx="5" ry="12" fill="#D97706" />
          <ellipse cx="88" cy="48" rx="4" ry="9" fill="#0F172A" stroke="#FFCC00" strokeWidth="1" />

          {/* Main 3D Spherical Head Shell */}
          <rect
            x="14"
            y="14"
            width="72"
            height="64"
            rx="30"
            fill="url(#botYellowHead)"
            stroke="#B45309"
            strokeWidth="1.2"
          />

          {/* Top Specular Curved Highlight */}
          <ellipse cx="50" cy="21" rx="22" ry="4.5" fill="rgba(255, 255, 255, 0.6)" />

          {/* Curved Black Visor Screen Border */}
          <rect
            x="20"
            y="22"
            width="60"
            height="50"
            rx="22"
            fill="#030712"
            stroke="#1E293B"
            strokeWidth="1.8"
          />

          {/* Inner Screen Glass Surface */}
          <rect
            x="22"
            y="24"
            width="56"
            height="46"
            rx="20"
            fill="url(#botVisorGlass)"
          />

          {/* Visor Glass Top Specular Glare Reflection */}
          <path
            d="M 28 26 Q 50 22 72 26 Q 68 34 50 32 Q 32 34 28 26 Z"
            fill="rgba(255, 255, 255, 0.15)"
          />

          {/* Dynamic LED Emotional Expression */}
          <g transform="translate(10, 0)">
            {renderVisorExpression()}
          </g>
        </g>
      </svg>
    </div>
  );
};
