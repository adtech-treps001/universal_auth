/**
 * Input Atom Component
 * 
 * Basic input component following atomic design principles.
 * Supports various input types, validation states, and accessibility features.
 */

import React, { forwardRef, InputHTMLAttributes } from 'react';
import { cn } from '../../utils/cn';

export interface InputProps extends Omit<InputHTMLAttributes<HTMLInputElement>, 'size'> {
  variant?: 'default' | 'filled' | 'outlined';
  size?: 'sm' | 'md' | 'lg';
  state?: 'default' | 'error' | 'success' | 'warning';
  label?: string;
  helperText?: string;
  errorMessage?: string;
  leftIcon?: React.ReactNode;
  rightIcon?: React.ReactNode;
  fullWidth?: boolean;
}

const Input = forwardRef<HTMLInputElement, InputProps>(
  (
    {
      className,
      variant = 'default',
      size = 'md',
      state = 'default',
      label,
      helperText,
      errorMessage,
      leftIcon,
      rightIcon,
      fullWidth = false,
      disabled,
      required,
      id,
      ...props
    },
    ref
  ) => {
    const inputId = id || `input-${Math.random().toString(36).slice(2, 11)}`;
    const hasError = state === 'error' || !!errorMessage;
    const displayHelperText = hasError ? errorMessage : helperText;

    const baseClasses = [
      'transition-colors duration-200 ease-in-out',
      'border rounded-md',
      'focus:outline-none focus:ring-2 focus:ring-offset-2',
      'disabled:opacity-50 disabled:cursor-not-allowed',
      'placeholder:text-gray-400'
    ];

    const variantClasses = {
      default: [
        'bg-white border-gray-300',
        'hover:border-gray-400',
        'focus:border-blue-500 focus:ring-blue-500'
      ],
      filled: [
        'bg-gray-50 border-gray-200',
        'hover:bg-gray-100 hover:border-gray-300',
        'focus:bg-white focus:border-blue-500 focus:ring-blue-500'
      ],
      outlined: [
        'bg-transparent border-2 border-gray-300',
        'hover:border-gray-400',
        'focus:border-blue-500 focus:ring-blue-500'
      ]
    };

    const sizeClasses = {
      sm: 'px-3 py-1.5 text-sm',
      md: 'px-3 py-2 text-base',
      lg: 'px-4 py-3 text-lg'
    };

    const stateClasses = {
      default: '',
      error: 'border-red-500 focus:border-red-500 focus:ring-red-500',
      success: 'border-green-500 focus:border-green-500 focus:ring-green-500',
      warning: 'border-yellow-500 focus:border-yellow-500 focus:ring-yellow-500'
    };

    const inputClasses = cn(
      baseClasses,
      variantClasses[variant],
      sizeClasses[size],
      stateClasses[state],
      {
        'w-full': fullWidth,
        'pl-10': leftIcon,
        'pr-10': rightIcon
      },
      className
    );

    return (
      <div className={cn('relative', { 'w-full': fullWidth })}>
        {label && (
          <label
            htmlFor={inputId}
            className={cn(
              'block text-sm font-medium mb-1',
              hasError ? 'text-red-700' : 'text-gray-700',
              disabled && 'text-gray-400'
            )}
          >
            {label}
            {required && <span className="text-red-500 ml-1">*</span>}
          </label>
        )}
        
        <div className="relative">
          {leftIcon && (
            <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
              <div className={cn(
                'text-gray-400',
                hasError && 'text-red-400',
                state === 'success' && 'text-green-400',
                state === 'warning' && 'text-yellow-400'
              )}>
                {leftIcon}
              </div>
            </div>
          )}
          
          <input
            ref={ref}
            id={inputId}
            className={inputClasses}
            disabled={disabled}
            required={required}
            aria-invalid={hasError}
            aria-describedby={displayHelperText ? `${inputId}-helper` : undefined}
            {...props}
          />
          
          {rightIcon && (
            <div className="absolute inset-y-0 right-0 pr-3 flex items-center pointer-events-none">
              <div className={cn(
                'text-gray-400',
                hasError && 'text-red-400',
                state === 'success' && 'text-green-400',
                state === 'warning' && 'text-yellow-400'
              )}>
                {rightIcon}
              </div>
            </div>
          )}
        </div>
        
        {displayHelperText && (
          <p
            id={`${inputId}-helper`}
            className={cn(
              'mt-1 text-sm',
              hasError ? 'text-red-600' : 'text-gray-500'
            )}
          >
            {displayHelperText}
          </p>
        )}
      </div>
    );
  }
);

Input.displayName = 'Input';

export default Input;