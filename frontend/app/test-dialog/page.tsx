// Copyright (c) 2025 Marco Pancotti
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//     http://www.apache.org/licenses/LICENSE-2.0
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

'use client';

import { useState } from 'react';
import { LikeButton } from '@/components/like-button';

export default function TestDialog() {
  const [message, setMessage] = useState('');
  
  const handleSuccess = () => {
    setMessage('Success! Feedback saved.');
  };
  
  const handleError = (error: string) => {
    setMessage(`Error: ${error}`);
  };
  
  return (
    <div className="min-h-screen p-8 bg-background">
      <div className="max-w-4xl mx-auto space-y-8">
        <h1 className="text-3xl font-bold">Test Dialog Positioning</h1>
        
        <div className="p-6 border rounded-lg bg-card">
          <h2 className="text-xl font-semibold mb-4">Like Button Test</h2>
          <p className="mb-4">Click the like button below to test the dialog positioning:</p>
          
          <div className="flex items-center gap-4">
            <LikeButton 
              enabled={true}
              workspaceId={1}
              onSuccess={handleSuccess}
              onError={handleError}
            />
            <span className="text-sm text-muted-foreground">← Click here to open dialog</span>
          </div>
          
          {message && (
            <div className="mt-4 p-3 rounded-lg bg-blue-100 dark:bg-blue-900/20 text-blue-900 dark:text-blue-100">
              {message}
            </div>
          )}
        </div>
        
        <div className="p-6 border rounded-lg bg-card">
          <h2 className="text-xl font-semibold mb-4">Expected Behavior</h2>
          <ul className="list-disc list-inside space-y-2 text-muted-foreground">
            <li>Dialog should appear centered on the screen</li>
            <li>Dialog should have a dark overlay behind it</li>
            <li>Dialog should have turquoise accents and proper styling</li>
            <li>Dialog should be dismissible via Cancel button or clicking outside</li>
          </ul>
        </div>
      </div>
    </div>
  );
}