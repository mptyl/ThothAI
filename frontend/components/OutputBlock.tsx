// Copyright (c) 2025 Marco Pancotti
// This file is part of ThothAI and is released under the Apache License 2.0.
// See the LICENSE.md file in the project root for full license information.

import React from 'react';

interface OutputBlockProps {
  imageSrc?: string;
  imageAlt?: string;
  children: React.ReactNode;
  className?: string;
  hideImage?: boolean;
}

/**
 * Standardized output block component for consistent layout across all output types.
 * Features:
 * - Consistent 4px padding (p-1)
 * - Standardized width with right margin (mr-[10%] w-[90%])
 * - 64x64px image container with proper vertical alignment
 * - 12px gap between image and content (gap-3)
 * - Consistent background and border styling
 */
export const OutputBlock: React.FC<OutputBlockProps> = ({
  imageSrc = '/dio-thoth-dx.png',
  imageAlt = 'ThothAI',
  children,
  className = '',
  hideImage = false
}) => {
  return (
    <div className={`mr-[10%] w-[90%] ${className}`}>
      <div className="flex items-start gap-3 p-1 bg-background/20 rounded-lg border border-border/20">
        {!hideImage && (
          <div className="flex-shrink-0 mt-0.5">
            <div className="w-16 h-16 rounded-full overflow-hidden flex items-center justify-center bg-background/10">
              <img 
                src={imageSrc}
                alt={imageAlt}
                className="w-16 h-16 object-contain"
              />
            </div>
          </div>
        )}
        <div className="flex-1 min-w-0">
          {children}
        </div>
      </div>
    </div>
  );
};