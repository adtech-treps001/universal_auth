/**
 * Utility function for merging class names
 * 
 * A lightweight alternative to clsx/classnames for combining CSS classes.
 * Handles conditional classes, arrays, and removes falsy values.
 */

type ClassValue = string | number | boolean | undefined | null | ClassArray | ClassObject;
type ClassArray = ClassValue[];
type ClassObject = Record<string, any>;

export function cn(...inputs: ClassValue[]): string {
  const classes: string[] = [];

  for (const input of inputs) {
    if (!input) continue;

    if (typeof input === 'string' || typeof input === 'number') {
      classes.push(String(input));
    } else if (Array.isArray(input)) {
      const nested = cn(...input);
      if (nested) classes.push(nested);
    } else if (typeof input === 'object') {
      for (const [key, value] of Object.entries(input)) {
        if (value) classes.push(key);
      }
    }
  }

  return classes.join(' ');
}

export default cn;