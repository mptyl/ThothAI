// Copyright (c) 2025 Tyl Consulting di Pancotti Marco
// Licensed under the Apache License, Version 2.0

'use client';

import { useEffect, useState } from 'react';
import { abortManager } from '@/lib/services/abort-manager';
import { sqlGeneratorApi } from '@/lib/sql-generator-api';

export default function TestAbortPage() {
  const [testResults, setTestResults] = useState<string[]>([]);
  
  useEffect(() => {
    // Run tests when component mounts
    runTests();
  }, []);
  
  const runTests = () => {
    const results: string[] = [];
    
    // Test 1: AbortManager is available
    if (abortManager) {
      results.push('OK: AbortManager is available');
      
      // Test 2: Create controller
      const controller = abortManager.createController('test-1');
      if (controller) {
        results.push('OK: Can create controller');
      } else {
        results.push('ERROR: Failed to create controller');
      }
      
      // Test 3: Check active count
      const count = abortManager.getActiveCount();
      results.push(`OK: Active controllers: ${count}`);
      
      // Test 4: Abort controller
      const aborted = abortManager.abort('test-1');
      results.push(`OK: Abort result: ${aborted}`);
      
      // Test 5: Check API client
      if (sqlGeneratorApi && typeof sqlGeneratorApi.cancelCurrentRequest === 'function') {
        results.push('OK: SQL API client has cancelCurrentRequest method');
      } else {
        results.push('ERROR: SQL API client missing cancelCurrentRequest method');
      }
      
    } else {
      results.push('ERROR: AbortManager not available');
    }
    
    setTestResults(results);
  };
  
  return (
    <div style={{ padding: '20px', fontFamily: 'monospace' }}>
      <h1>AbortManager Test Page</h1>
      <h2>Test Results:</h2>
      <ul>
        {testResults.map((result, index) => (
          <li key={index}>{result}</li>
        ))}
      </ul>
      <button onClick={runTests} style={{ marginTop: '20px' }}>
        Run Tests Again
      </button>
      <div style={{ marginTop: '20px' }}>
        <h3>Manual Testing:</h3>
        <p>Open browser console and run:</p>
        <pre style={{ background: '#f0f0f0', padding: '10px' }}>
{`window.__abortManager
window.__abortManager.createController('test')
window.__abortManager.getActiveCount()
window.__abortManager.abort('test')`}
        </pre>
      </div>
    </div>
  );
}