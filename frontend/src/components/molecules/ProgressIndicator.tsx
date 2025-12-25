/**
 * ProgressIndicator Molecule Component
 * 
 * Visual progress indicator for multi-step processes like progressive profiling.
 * Supports various styles and configurations.
 */

import React from 'react';
import { cn } from '../../utils/cn';
import Icon from '../atoms/Icon';

export interface ProgressStep {
  id: string;
  label: string;
  description?: string;
  completed?: boolean;
  current?: boolean;
  optional?: boolean;
}

export interface ProgressIndicatorProps {
  steps: ProgressStep[];
  variant?: 'linear' | 'circular' | 'dots' | 'numbered';
  size?: 'sm' | 'md' | 'lg';
  showLabels?: boolean;
  showDescriptions?: boolean;
  className?: string;
  onStepClick?: (step: ProgressStep, index: number) => void;
  allowClickableSteps?: boolean;
}

const ProgressIndicator: React.FC<ProgressIndicatorProps> = ({
  steps,
  variant = 'linear',
  size = 'md',
  showLabels = true,
  showDescriptions = false,
  className,
  onStepClick,
  allowClickableSteps = false
}) => {
  const currentStepIndex = steps.findIndex(step => step.current);
  const completedSteps = steps.filter(step => step.completed).length;
  const totalSteps = steps.length;
  const progressPercentage = (completedSteps / totalSteps) * 100;

  if (variant === 'circular') {
    return (
      <div className={cn('flex items-center justify-center', className)}>
        <div className="relative">
          <svg
            className={cn(
              'transform -rotate-90',
              size === 'sm' && 'w-16 h-16',
              size === 'md' && 'w-24 h-24',
              size === 'lg' && 'w-32 h-32'
            )}
            viewBox="0 0 100 100"
          >
            {/* Background circle */}
            <circle
              cx="50"
              cy="50"
              r="45"
              fill="none"
              stroke="currentColor"
              strokeWidth="8"
              className="text-gray-200"
            />
            {/* Progress circle */}
            <circle
              cx="50"
              cy="50"
              r="45"
              fill="none"
              stroke="currentColor"
              strokeWidth="8"
              strokeLinecap="round"
              strokeDasharray={`${progressPercentage * 2.83} 283`}
              className="text-blue-600 transition-all duration-500 ease-out"
            />
          </svg>
          <div className="absolute inset-0 flex items-center justify-center">
            <div className="text-center">
              <div className={cn(
                'font-bold text-gray-900',
                size === 'sm' && 'text-sm',
                size === 'md' && 'text-lg',
                size === 'lg' && 'text-xl'
              )}>
                {Math.round(progressPercentage)}%
              </div>
              {showLabels && (
                <div className={cn(
                  'text-gray-500',
                  size === 'sm' && 'text-xs',
                  size === 'md' && 'text-sm',
                  size === 'lg' && 'text-base'
                )}>
                  {completedSteps} of {totalSteps}
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    );
  }

  if (variant === 'dots') {
    return (
      <div className={cn('flex items-center justify-center space-x-2', className)}>
        {steps.map((step, index) => (
          <button
            key={step.id}
            onClick={() => allowClickableSteps && onStepClick?.(step, index)}
            disabled={!allowClickableSteps}
            className={cn(
              'rounded-full transition-all duration-200',
              size === 'sm' && 'w-2 h-2',
              size === 'md' && 'w-3 h-3',
              size === 'lg' && 'w-4 h-4',
              step.completed && 'bg-green-500',
              step.current && 'bg-blue-500',
              !step.completed && !step.current && 'bg-gray-300',
              allowClickableSteps && 'hover:scale-110 cursor-pointer',
              !allowClickableSteps && 'cursor-default'
            )}
            aria-label={`Step ${index + 1}: ${step.label}`}
            title={step.label}
          />
        ))}
      </div>
    );
  }

  if (variant === 'numbered') {
    return (
      <div className={cn('flex items-center', className)}>
        {steps.map((step, index) => (
          <React.Fragment key={step.id}>
            <div className="flex flex-col items-center">
              <button
                onClick={() => allowClickableSteps && onStepClick?.(step, index)}
                disabled={!allowClickableSteps}
                className={cn(
                  'flex items-center justify-center rounded-full font-semibold transition-all duration-200',
                  size === 'sm' && 'w-8 h-8 text-sm',
                  size === 'md' && 'w-10 h-10 text-base',
                  size === 'lg' && 'w-12 h-12 text-lg',
                  step.completed && 'bg-green-500 text-white',
                  step.current && 'bg-blue-500 text-white',
                  !step.completed && !step.current && 'bg-gray-200 text-gray-600',
                  allowClickableSteps && 'hover:scale-105 cursor-pointer',
                  !allowClickableSteps && 'cursor-default'
                )}
                aria-label={`Step ${index + 1}: ${step.label}`}
              >
                {step.completed ? (
                  <Icon name="check" size={size === 'sm' ? 'xs' : size === 'md' ? 'sm' : 'md'} />
                ) : (
                  index + 1
                )}
              </button>
              
              {showLabels && (
                <div className="mt-2 text-center">
                  <div className={cn(
                    'font-medium',
                    size === 'sm' && 'text-xs',
                    size === 'md' && 'text-sm',
                    size === 'lg' && 'text-base',
                    step.current && 'text-blue-600',
                    step.completed && 'text-green-600',
                    !step.completed && !step.current && 'text-gray-500'
                  )}>
                    {step.label}
                    {step.optional && (
                      <span className="text-gray-400 ml-1">(optional)</span>
                    )}
                  </div>
                  
                  {showDescriptions && step.description && (
                    <div className={cn(
                      'text-gray-500 mt-1',
                      size === 'sm' && 'text-xs',
                      size === 'md' && 'text-xs',
                      size === 'lg' && 'text-sm'
                    )}>
                      {step.description}
                    </div>
                  )}
                </div>
              )}
            </div>
            
            {index < steps.length - 1 && (
              <div className={cn(
                'flex-1 h-px bg-gray-300 mx-4',
                step.completed && 'bg-green-500'
              )} />
            )}
          </React.Fragment>
        ))}
      </div>
    );
  }

  // Default: linear variant
  return (
    <div className={cn('w-full', className)}>
      {/* Progress bar */}
      <div className={cn(
        'w-full bg-gray-200 rounded-full overflow-hidden',
        size === 'sm' && 'h-2',
        size === 'md' && 'h-3',
        size === 'lg' && 'h-4'
      )}>
        <div
          className="h-full bg-blue-500 transition-all duration-500 ease-out"
          style={{ width: `${progressPercentage}%` }}
        />
      </div>
      
      {/* Step indicators */}
      <div className="flex justify-between mt-2">
        {steps.map((step, index) => (
          <button
            key={step.id}
            onClick={() => allowClickableSteps && onStepClick?.(step, index)}
            disabled={!allowClickableSteps}
            className={cn(
              'flex flex-col items-center transition-all duration-200',
              allowClickableSteps && 'hover:scale-105 cursor-pointer',
              !allowClickableSteps && 'cursor-default'
            )}
            style={{ width: `${100 / steps.length}%` }}
          >
            <div className={cn(
              'rounded-full flex items-center justify-center',
              size === 'sm' && 'w-6 h-6',
              size === 'md' && 'w-8 h-8',
              size === 'lg' && 'w-10 h-10',
              step.completed && 'bg-green-500 text-white',
              step.current && 'bg-blue-500 text-white',
              !step.completed && !step.current && 'bg-gray-300 text-gray-600'
            )}>
              {step.completed ? (
                <Icon name="check" size={size === 'sm' ? 'xs' : 'sm'} />
              ) : (
                <div className={cn(
                  'w-2 h-2 rounded-full',
                  step.current && 'bg-white',
                  !step.current && 'bg-current'
                )} />
              )}
            </div>
            
            {showLabels && (
              <div className="mt-1 text-center">
                <div className={cn(
                  'font-medium',
                  size === 'sm' && 'text-xs',
                  size === 'md' && 'text-sm',
                  size === 'lg' && 'text-base',
                  step.current && 'text-blue-600',
                  step.completed && 'text-green-600',
                  !step.completed && !step.current && 'text-gray-500'
                )}>
                  {step.label}
                  {step.optional && (
                    <span className="text-gray-400 ml-1">(opt)</span>
                  )}
                </div>
                
                {showDescriptions && step.description && (
                  <div className={cn(
                    'text-gray-500 mt-1',
                    size === 'sm' && 'text-xs',
                    size === 'md' && 'text-xs',
                    size === 'lg' && 'text-sm'
                  )}>
                    {step.description}
                  </div>
                )}
              </div>
            )}
          </button>
        ))}
      </div>
    </div>
  );
};

export default ProgressIndicator;