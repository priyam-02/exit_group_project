import React from 'react';

interface CardProps {
  children: React.ReactNode;
  className?: string;
  hover?: boolean;
}

export const Card: React.FC<CardProps> = ({
  children,
  className = '',
  hover = false,
}) => {
  return (
    <div className={`terminal-card ${hover ? 'glass-hover' : ''} ${className}`}>
      {children}
    </div>
  );
};
