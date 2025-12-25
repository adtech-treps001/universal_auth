/**
 * SocialButton Molecule Component
 * 
 * Specialized button for social authentication providers.
 * Combines Button atom with provider-specific styling and icons.
 */

import React from 'react';
import Button, { ButtonProps } from '../atoms/Button';
import Icon from '../atoms/Icon';
import { cn } from '../../utils/cn';

export interface SocialButtonProps extends Omit<ButtonProps, 'leftIcon' | 'variant'> {
  provider: 'google' | 'github' | 'linkedin' | 'apple' | 'meta' | 'microsoft';
  showIcon?: boolean;
  showText?: boolean;
  text?: string;
}

const providerConfig = {
  google: {
    name: 'Google',
    bgColor: 'bg-white',
    textColor: 'text-gray-700',
    borderColor: 'border-gray-300',
    hoverBg: 'hover:bg-gray-50',
    icon: (
      <svg viewBox="0 0 24 24" className="w-5 h-5">
        <path
          fill="#4285F4"
          d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
        />
        <path
          fill="#34A853"
          d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
        />
        <path
          fill="#FBBC05"
          d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"
        />
        <path
          fill="#EA4335"
          d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"
        />
      </svg>
    )
  },
  github: {
    name: 'GitHub',
    bgColor: 'bg-gray-900',
    textColor: 'text-white',
    borderColor: 'border-gray-900',
    hoverBg: 'hover:bg-gray-800',
    icon: (
      <svg viewBox="0 0 24 24" fill="currentColor" className="w-5 h-5">
        <path d="M12 0c-6.626 0-12 5.373-12 12 0 5.302 3.438 9.8 8.207 11.387.599.111.793-.261.793-.577v-2.234c-3.338.726-4.033-1.416-4.033-1.416-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.729.083-.729 1.205.084 1.839 1.237 1.839 1.237 1.07 1.834 2.807 1.304 3.492.997.107-.775.418-1.305.762-1.604-2.665-.305-5.467-1.334-5.467-5.931 0-1.311.469-2.381 1.236-3.221-.124-.303-.535-1.524.117-3.176 0 0 1.008-.322 3.301 1.23.957-.266 1.983-.399 3.003-.404 1.02.005 2.047.138 3.006.404 2.291-1.552 3.297-1.23 3.297-1.23.653 1.653.242 2.874.118 3.176.77.84 1.235 1.911 1.235 3.221 0 4.609-2.807 5.624-5.479 5.921.43.372.823 1.102.823 2.222v3.293c0 .319.192.694.801.576 4.765-1.589 8.199-6.086 8.199-11.386 0-6.627-5.373-12-12-12z"/>
      </svg>
    )
  },
  linkedin: {
    name: 'LinkedIn',
    bgColor: 'bg-blue-700',
    textColor: 'text-white',
    borderColor: 'border-blue-700',
    hoverBg: 'hover:bg-blue-800',
    icon: (
      <svg viewBox="0 0 24 24" fill="currentColor" className="w-5 h-5">
        <path d="M20.447 20.452h-3.554v-5.569c0-1.328-.027-3.037-1.852-3.037-1.853 0-2.136 1.445-2.136 2.939v5.667H9.351V9h3.414v1.561h.046c.477-.9 1.637-1.85 3.37-1.85 3.601 0 4.267 2.37 4.267 5.455v6.286zM5.337 7.433c-1.144 0-2.063-.926-2.063-2.065 0-1.138.92-2.063 2.063-2.063 1.14 0 2.064.925 2.064 2.063 0 1.139-.925 2.065-2.064 2.065zm1.782 13.019H3.555V9h3.564v11.452zM22.225 0H1.771C.792 0 0 .774 0 1.729v20.542C0 23.227.792 24 1.771 24h20.451C23.2 24 24 23.227 24 22.271V1.729C24 .774 23.2 0 22.222 0h.003z"/>
      </svg>
    )
  },
  apple: {
    name: 'Apple',
    bgColor: 'bg-black',
    textColor: 'text-white',
    borderColor: 'border-black',
    hoverBg: 'hover:bg-gray-800',
    icon: (
      <svg viewBox="0 0 24 24" fill="currentColor" className="w-5 h-5">
        <path d="M12.017 0C8.396 0 8.025.044 8.025.044c-2.981.043-5.393 2.414-5.393 5.393 0 0-.044.371-.044 4.017 0 3.646.044 4.017.044 4.017 0 2.979 2.412 5.35 5.393 5.393 0 0 .371.044 4.017.044 3.646 0 4.017-.044 4.017-.044 2.981-.043 5.393-2.414 5.393-5.393 0 0 .044-.371.044-4.017 0-3.646-.044-4.017-.044-4.017 0-2.979-2.412-5.35-5.393-5.393 0 0-.371-.044-4.017-.044zm0 1.441c3.563 0 3.901.016 5.281.076 1.274.058 1.965.27 2.427.448.61.237 1.045.52 1.502.977.457.457.74.892.977 1.502.178.462.39 1.153.448 2.427.06 1.38.076 1.718.076 5.281s-.016 3.901-.076 5.281c-.058 1.274-.27 1.965-.448 2.427-.237.61-.52 1.045-.977 1.502-.457.457-.892.74-1.502.977-.462.178-1.153.39-2.427.448-1.38.06-1.718.076-5.281.076s-3.901-.016-5.281-.076c-1.274-.058-1.965-.27-2.427-.448-.61-.237-1.045-.52-1.502-.977-.457-.457-.74-.892-.977-1.502-.178-.462-.39-1.153-.448-2.427-.06-1.38-.076-1.718-.076-5.281s.016-3.901.076-5.281c.058-1.274.27-1.965.448-2.427.237-.61.52-1.045.977-1.502.457-.457.892-.74 1.502-.977.462-.178 1.153-.39 2.427-.448 1.38-.06 1.718-.076 5.281-.076z"/>
        <path d="M12.017 5.838a6.162 6.162 0 1 0 0 12.324 6.162 6.162 0 0 0 0-12.324zm0 10.162a4 4 0 1 1 0-8 4 4 0 0 1 0 8zm7.846-10.405a1.441 1.441 0 0 1-2.88 0 1.441 1.441 0 0 1 2.88 0z"/>
      </svg>
    )
  },
  meta: {
    name: 'Meta',
    bgColor: 'bg-blue-600',
    textColor: 'text-white',
    borderColor: 'border-blue-600',
    hoverBg: 'hover:bg-blue-700',
    icon: (
      <svg viewBox="0 0 24 24" fill="currentColor" className="w-5 h-5">
        <path d="M24 12.073c0-6.627-5.373-12-12-12s-12 5.373-12 12c0 5.99 4.388 10.954 10.125 11.854v-8.385H7.078v-3.47h3.047V9.43c0-3.007 1.792-4.669 4.533-4.669 1.312 0 2.686.235 2.686.235v2.953H15.83c-1.491 0-1.956.925-1.956 1.874v2.25h3.328l-.532 3.47h-2.796v8.385C19.612 23.027 24 18.062 24 12.073z"/>
      </svg>
    )
  },
  microsoft: {
    name: 'Microsoft',
    bgColor: 'bg-white',
    textColor: 'text-gray-700',
    borderColor: 'border-gray-300',
    hoverBg: 'hover:bg-gray-50',
    icon: (
      <svg viewBox="0 0 24 24" fill="currentColor" className="w-5 h-5">
        <path fill="#f25022" d="M1 1h10v10H1z"/>
        <path fill="#00a4ef" d="M13 1h10v10H13z"/>
        <path fill="#7fba00" d="M1 13h10v10H1z"/>
        <path fill="#ffb900" d="M13 13h10v10H13z"/>
      </svg>
    )
  }
};

const SocialButton: React.FC<SocialButtonProps> = ({
  provider,
  showIcon = true,
  showText = true,
  text,
  className,
  children,
  ...props
}) => {
  const config = providerConfig[provider];
  const displayText = text || `Continue with ${config.name}`;

  const buttonClasses = cn(
    config.bgColor,
    config.textColor,
    config.borderColor,
    config.hoverBg,
    'border transition-colors duration-200',
    'focus:ring-2 focus:ring-offset-2 focus:ring-blue-500',
    className
  );

  return (
    <Button
      className={buttonClasses}
      leftIcon={showIcon ? config.icon : undefined}
      {...props}
    >
      {children || (showText && displayText)}
    </Button>
  );
};

export default SocialButton;