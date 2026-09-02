import React, { useEffect, useRef } from 'react';

interface IndustrialBackgroundProps {
  theme?: 'dark' | 'light';
}

interface Particle {
  x: number;
  y: number;
  vx: number;
  vy: number;
  size: number;
  alpha: number;
  baseAlpha: number;
  color: string;
}

export const IndustrialBackground: React.FC<IndustrialBackgroundProps> = ({ theme = 'dark' }) => {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const isDark = theme === 'dark';

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    let animationFrameId: number;
    let width = (canvas.width = window.innerWidth);
    let height = (canvas.height = window.innerHeight);

    const handleResize = () => {
      if (!canvas) return;
      width = canvas.width = window.innerWidth;
      height = canvas.height = window.innerHeight;
    };

    window.addEventListener('resize', handleResize);

    // Particle Palette
    const colors = isDark
      ? ['rgba(255, 0, 0, ', 'rgba(255, 60, 60, ', 'rgba(0, 229, 255, ', 'rgba(255, 255, 255, ']
      : ['rgba(220, 38, 38, ', 'rgba(239, 68, 68, ', 'rgba(2, 132, 199, ', 'rgba(100, 116, 139, '];

    const particleCount = Math.min(Math.floor((width * height) / 22000), 55);
    const particles: Particle[] = [];

    for (let i = 0; i < particleCount; i++) {
      const baseAlpha = Math.random() * 0.45 + 0.15;
      particles.push({
        x: Math.random() * width,
        y: Math.random() * height,
        vx: (Math.random() - 0.5) * 0.45,
        vy: (Math.random() - 0.5) * 0.45,
        size: Math.random() * 2 + 1,
        alpha: baseAlpha,
        baseAlpha,
        color: colors[Math.floor(Math.random() * colors.length)],
      });
    }

    let tick = 0;

    const render = () => {
      ctx.clearRect(0, 0, width, height);
      tick += 0.015;

      // Draw subtle connecting constellation lines between nearby particles
      const maxDistance = 110;
      for (let i = 0; i < particles.length; i++) {
        for (let j = i + 1; j < particles.length; j++) {
          const dx = particles[i].x - particles[j].x;
          const dy = particles[i].y - particles[j].y;
          const dist = Math.sqrt(dx * dx + dy * dy);

          if (dist < maxDistance) {
            const lineAlpha = (1 - dist / maxDistance) * (isDark ? 0.12 : 0.08);
            ctx.beginPath();
            ctx.moveTo(particles[i].x, particles[i].y);
            ctx.lineTo(particles[j].x, particles[j].y);
            ctx.strokeStyle = isDark
              ? `rgba(255, 0, 0, ${lineAlpha})`
              : `rgba(220, 38, 38, ${lineAlpha})`;
            ctx.lineWidth = 0.75;
            ctx.stroke();
          }
        }
      }

      // Update and Draw Particles
      for (let i = 0; i < particles.length; i++) {
        const p = particles[i];
        p.x += p.vx;
        p.y += p.vy;

        // Wrap around screen edges
        if (p.x < 0) p.x = width;
        if (p.x > width) p.x = 0;
        if (p.y < 0) p.y = height;
        if (p.y > height) p.y = 0;

        // Gentle breathing pulse
        const pulse = Math.sin(tick + i) * 0.15;
        const currentAlpha = Math.max(0.05, Math.min(0.8, p.baseAlpha + pulse));

        ctx.beginPath();
        ctx.arc(p.x, p.y, p.size, 0, Math.PI * 2);
        ctx.fillStyle = `${p.color}${currentAlpha})`;
        ctx.shadowColor = isDark ? '#FF0000' : '#DC2626';
        ctx.shadowBlur = p.size > 2 ? 6 : 0;
        ctx.fill();
        ctx.shadowBlur = 0;
      }

      animationFrameId = requestAnimationFrame(render);
    };

    render();

    return () => {
      window.removeEventListener('resize', handleResize);
      cancelAnimationFrame(animationFrameId);
    };
  }, [isDark]);

  return (
    <div
      className="industrial-bg-container"
      aria-hidden="true"
      style={{
        position: 'fixed',
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        width: '100vw',
        height: '100vh',
        overflow: 'hidden',
        pointerEvents: 'none',
        zIndex: 1,
      }}
    >
      {/* Interactive High-Performance Fine Particle Canvas */}
      <canvas
        ref={canvasRef}
        style={{
          position: 'absolute',
          top: 0,
          left: 0,
          width: '100%',
          height: '100%',
        }}
      />
    </div>
  );
};
