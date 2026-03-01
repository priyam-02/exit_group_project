import React from 'react';

interface BadgeProps {
  children: React.ReactNode;
  variant?: 'blue' | 'green' | 'purple' | 'orange' | 'red' | 'yellow';
  className?: string;
}

export const Badge: React.FC<BadgeProps> = ({
  children,
  variant = 'blue',
  className = '',
}) => {
  const variantClasses = {
    blue: 'badge-blue',
    green: 'badge-green',
    purple: 'badge-purple',
    orange: 'badge-orange',
    red: 'badge-red',
    yellow: 'badge-yellow',
  };

  return (
    <span className={`badge ${variantClasses[variant]} ${className}`}>
      {children}
    </span>
  );
};
