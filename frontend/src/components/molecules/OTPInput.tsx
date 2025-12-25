"use client";

/**
 * OTPInput Molecule Component
 * 
 * Specialized input component for OTP (One-Time Password) entry.
 * Provides individual digit inputs with automatic focus management.
 */

import React, { useState, useRef, useEffect, KeyboardEvent, ClipboardEvent } from 'react';
import { cn } from '../../utils/cn';

export interface OTPInputProps {
  length?: number;
  value?: string;
  onChange?: (value: string) => void;
  onComplete?: (value: string) => void;
  disabled?: boolean;
  error?: boolean;
  autoFocus?: boolean;
  placeholder?: string;
  className?: string;
  inputClassName?: string;
  size?: 'sm' | 'md' | 'lg';
  variant?: 'default' | 'filled' | 'outlined';
}

const OTPInput: React.FC<OTPInputProps> = ({
  length = 6,
  value = '',
  onChange,
  onComplete,
  disabled = false,
  error = false,
  autoFocus = false,
  placeholder = '○',
  className,
  inputClassName,
  size = 'md',
  variant = 'default'
}) => {
  const [digits, setDigits] = useState<string[]>(
    Array.from({ length }, (_, i) => value[i] || '')
  );
  const inputRefs = useRef<(HTMLInputElement | null)[]>([]);

  // Update digits when value prop changes
  useEffect(() => {
    const newDigits = Array.from({ length }, (_, i) => value[i] || '');
    setDigits(newDigits);
  }, [value, length]);

  // Auto-focus first input
  useEffect(() => {
    if (autoFocus && inputRefs.current[0]) {
      inputRefs.current[0].focus();
    }
  }, [autoFocus]);

  const handleChange = (index: number, digit: string) => {
    // Only allow single digits
    if (digit.length > 1) {
      digit = digit.slice(-1);
    }

    // Only allow numeric input
    if (digit && !/^\d$/.test(digit)) {
      return;
    }

    const newDigits = [...digits];
    newDigits[index] = digit;
    setDigits(newDigits);

    const newValue = newDigits.join('');
    onChange?.(newValue);

    // Auto-focus next input
    if (digit && index < length - 1) {
      inputRefs.current[index + 1]?.focus();
    }

    // Call onComplete when all digits are filled
    if (newValue.length === length) {
      onComplete?.(newValue);
    }
  };

  const handleKeyDown = (index: number, e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Backspace') {
      if (!digits[index] && index > 0) {
        // Move to previous input if current is empty
        inputRefs.current[index - 1]?.focus();
      } else {
        // Clear current input
        handleChange(index, '');
      }
    } else if (e.key === 'ArrowLeft' && index > 0) {
      inputRefs.current[index - 1]?.focus();
    } else if (e.key === 'ArrowRight' && index < length - 1) {
      inputRefs.current[index + 1]?.focus();
    } else if (e.key === 'Delete') {
      handleChange(index, '');
    }
  };

  const handlePaste = (e: ClipboardEvent<HTMLInputElement>) => {
    e.preventDefault();
    const pastedData = e.clipboardData.getData('text/plain');
    const pastedDigits = pastedData.replace(/\D/g, '').slice(0, length);
    
    if (pastedDigits) {
      const newDigits = Array.from({ length }, (_, i) => pastedDigits[i] || '');
      setDigits(newDigits);
      
      const newValue = newDigits.join('');
      onChange?.(newValue);
      
      // Focus the next empty input or the last input
      const nextEmptyIndex = newDigits.findIndex(digit => !digit);
      const focusIndex = nextEmptyIndex !== -1 ? nextEmptyIndex : length - 1;
      inputRefs.current[focusIndex]?.focus();
      
      if (newValue.length === length) {
        onComplete?.(newValue);
      }
    }
  };

  const handleFocus = (index: number) => {
    // Select all text when focusing
    inputRefs.current[index]?.select();
  };

  const sizeClasses = {
    sm: 'w-8 h-8 text-sm',
    md: 'w-12 h-12 text-lg',
    lg: 'w-16 h-16 text-xl'
  };

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

  const baseInputClasses = [
    'text-center font-mono font-semibold',
    'border rounded-md',
    'transition-all duration-200 ease-in-out',
    'focus:outline-none focus:ring-2 focus:ring-offset-2',
    'disabled:opacity-50 disabled:cursor-not-allowed',
    'select-all'
  ];

  const inputClasses = cn(
    baseInputClasses,
    variantClasses[variant],
    sizeClasses[size],
    {
      'border-red-500 focus:border-red-500 focus:ring-red-500': error,
      'ring-red-500': error
    },
    inputClassName
  );

  return (
    <div className={cn('flex gap-2 justify-center', className)}>
      {Array.from({ length }, (_, index) => (
        <input
          key={index}
          ref={(el) => { inputRefs.current[index] = el; }}
          type="text"
          inputMode="numeric"
          pattern="\d*"
          maxLength={1}
          value={digits[index]}
          onChange={(e) => handleChange(index, e.target.value)}
          onKeyDown={(e) => handleKeyDown(index, e)}
          onPaste={handlePaste}
          onFocus={() => handleFocus(index)}
          disabled={disabled}
          placeholder={placeholder}
          className={inputClasses}
          aria-label={`Digit ${index + 1} of ${length}`}
          autoComplete="one-time-code"
        />
      ))}
    </div>
  );
};

export default OTPInput;