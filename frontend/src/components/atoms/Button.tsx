/**
 * Button Atom Component
 * 
 * Versatile button component following atomic design principles.
 * Supports various variants, sizes, states, and accessibility features.
 */

import React, { forwardRef, ButtonHTMLAttributes } from 'react';
import { cn } from '../../utils/cn';

export interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'outline' | 'ghost' | 'link' | 'danger';
  size?: 'xs' | 'sm' | 'md' | 'lg' | 'xl';
  loading?: boolean;
  leftIcon?: React.ReactNode;
  rightIcon?: React.ReactNode;
  fullWidth?: boolean;
  rounded?: boolean;
}

const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  (
    {
      className,
      variant = 'primary',
      size = 'md',
      loading = false,
      leftIcon,
      rightIcon,
      fullWidth = false,
      rounded = false,
      disabled,
      children,
      ...props
    },
    ref
  ) => {
    const isDisabled = disabled || loading;

    const baseClasses = [
      'inline-flex items-center justify-center',
      'font-medium transition-all duration-200 ease-in-out',
      'focus:outline-none focus:ring-2 focus:ring-offset-2',
      'disabled:opacity-50 disabled:cursor-not-allowed',
      'select-none'
    ];

    const variantClasses = {
      primary: [
        'bg-blue-600 text-white border border-transparent',
        'hover:bg-blue-700 active:bg-blue-800',
        'focus:ring-blue-500',
        'disabled:hover:bg-blue-600'
      ],
      secondary: [
        'bg-gray-600 text-white border border-transparent',
        'hover:bg-gray-700 active:bg-gray-800',
        'focus:ring-gray-500',
        'disabled:hover:bg-gray-600'
      ],
      outline: [
        'bg-transparent text-blue-600 border border-blue-600',
        'hover:bg-blue-50 active:bg-blue-100',
        'focus:ring-blue-500',
        'disabled:hover:bg-transparent'
      ],
      ghost: [
        'bg-transparent text-gray-700 border border-transparent',
        'hover:bg-gray-100 active:bg-gray-200',
        'focus:ring-gray-500',
        'disabled:hover:bg-transparent'
      ],
      link: [
        'bg-transparent text-blue-600 border border-transparent',
        'hover:text-blue-800 hover:underline',
        'focus:ring-blue-500',
        'disabled:hover:text-blue-600 disabled:hover:no-underline'
      ],
      danger: [
        'bg-red-600 text-white border border-transparent',
        'hover:bg-red-700 active:bg-red-800',
        'focus:ring-red-500',
        'disabled:hover:bg-red-600'
      ]
    };

    const sizeClasses = {
      xs: 'px-2 py-1 text-xs',
      sm: 'px-3 py-1.5 text-sm',
      md: 'px-4 py-2 text-base',
      lg: 'px-6 py-3 text-lg',
      xl: 'px-8 py-4 text-xl'
    };

    const roundedClasses = {
      xs: rounded ? 'rounded-full' : 'rounded',
      sm: rounded ? 'rounded-full' : 'rounded-md',
      md: rounded ? 'rounded-full' : 'rounded-md',
      lg: rounded ? 'rounded-full' : 'rounded-lg',
      xl: rounded ? 'rounded-full' : 'rounded-lg'
    };

    const buttonClasses = cn(
      baseClasses,
      variantClasses[variant],
      sizeClasses[size],
      roundedClasses[size],
      {
        'w-full': fullWidth,
        'cursor-wait': loading
      },
      className
    );

    const LoadingSpinner = () => (
      <svg
        className="animate-spin -ml-1 mr-2 h-4 w-4"
        xmlns="http://www.w3.org/2000/svg"
        fill="none"
        viewBox="0 0 24 24"
      >
        <circle
          className="opacity-25"
          cx="12"
          cy="12"
          r="10"
          stroke="currentColor"
          strokeWidth="4"
        />
        <path
          className="opacity-75"
          fill="currentColor"
          d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
        />
      </svg>
    );

    return (
      <button
        ref={ref}
        className={buttonClasses}
        disabled={isDisabled}
        aria-disabled={isDisabled}
        {...props}
      >
        {loading && <LoadingSpinner />}
        {!loading && leftIcon && (
          <span className="mr-2 flex-shrink-0">{leftIcon}</span>
        )}
        
        {children && (
          <span className={cn(
            'truncate',
            (leftIcon || loading) && !rightIcon && 'ml-0',
            rightIcon && !leftIcon && !loading && 'mr-0'
          )}>
            {children}
          </span>
        )}
        
        {!loading && rightIcon && (
          <span className="ml-2 flex-shrink-0">{rightIcon}</span>
        )}
      </button>
    );
  }
);

Button.displayName = 'Button';

export default Button;