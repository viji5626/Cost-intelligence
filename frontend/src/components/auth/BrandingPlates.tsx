import React from 'react';

interface BrandingPlatesProps {
  theme?: 'dark' | 'light';
  layout?: 'corner' | 'inline';
}

export const BrandingPlates: React.FC<BrandingPlatesProps> = ({
  theme = 'dark',
  layout = 'corner',
}) => {
  const isDark = theme === 'dark';

  const tascSrc = isDark ? '/assets/tasc_plate_dark.png' : '/assets/tasc_plate_light.png';
  const heroCimSrc = isDark ? '/assets/hero_cim_plate_dark.png' : '/assets/hero_cim_plate_light.png';

  if (layout === 'inline') {
    return (
      <div className="auth-branding-plates-inline">
        <div className="auth-plate-wrapper">
          <img
            src={heroCimSrc}
            alt="Powered by Hero CIM™ — Hero Cost Intelligence Model"
            className="auth-plate-img"
          />
        </div>
        <div className="auth-plate-wrapper">
          <img
            src={tascSrc}
            alt="Engineered & Developed by Tenacious Automation (TASC)"
            className="auth-plate-img"
          />
        </div>
      </div>
    );
  }

  return (
    <>
      {/* Bottom Left: Hero CIM Plate */}
      <div className="auth-branding-plate-corner left">
        <div className="auth-plate-wrapper">
          <img
            src={heroCimSrc}
            alt="Powered by Hero CIM™ — Hero Cost Intelligence Model"
            className="auth-plate-img"
          />
        </div>
      </div>

      {/* Bottom Right: TASC Plate */}
      <div className="auth-branding-plate-corner right">
        <div className="auth-plate-wrapper">
          <img
            src={tascSrc}
            alt="Engineered & Developed by Tenacious Automation (TASC)"
            className="auth-plate-img"
          />
        </div>
      </div>
    </>
  );
};
