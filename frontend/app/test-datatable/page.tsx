// Copyright (c) 2025 Marco Pancotti
// This file is part of ThothAI and is released under the Apache License 2.0.
// See the LICENSE.md file in the project root for full license information.

'use client';

import React, { useState } from 'react';
import { DataTable } from '@/components/DataTable';
import { Button } from '@/components/ui/button';

export default function TestDataTablePage() {
  const [testData, setTestData] = useState<any[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Simulate the exact format that the backend sends
  const loadTestData1 = () => {
    // This simulates the format from: SELECT CDSCode FROM frpm WHERE ...
    const fakeData = [
      { "CDSCode": "01234567890123" },
      { "CDSCode": "01234567890124" },
      { "CDSCode": "01234567890125" },
      { "CDSCode": "01234567890126" },
      { "CDSCode": "01234567890127" },
    ];
    setTestData(fakeData);
    setError(null);
  };

  const loadTestData2 = () => {
    // This simulates a more complex query result
    const fakeData = [
      { 
        "CDSCode": "01234567890123",
        "School Name": "Test Elementary School",
        "District": "Test District",
        "Enrollment": 450,
        "Type": "Elementary"
      },
      { 
        "CDSCode": "01234567890124",
        "School Name": "Test Middle School",
        "District": "Test District",
        "Enrollment": 620,
        "Type": "Middle"
      },
      { 
        "CDSCode": "01234567890125",
        "School Name": "Test High School",
        "District": "Test District",
        "Enrollment": 1200,
        "Type": "High"
      },
    ];
    setTestData(fakeData);
    setError(null);
  };

  const loadTestData3 = () => {
    // Test with 1000 rows as the backend sends
    const fakeData = Array.from({ length: 1000 }, (_, i) => ({
      "CDSCode": `0123456789${String(i).padStart(4, '0')}`,
      "Row_Number": i + 1,
      "Random_Value": Math.floor(Math.random() * 1000)
    }));
    setTestData(fakeData);
    setError(null);
  };

  const simulateLoading = () => {
    setIsLoading(true);
    setTestData([]);
    setError(null);
    setTimeout(() => {
      setIsLoading(false);
      loadTestData2();
    }, 2000);
  };

  const simulateError = () => {
    setTestData([]);
    setError("Test error: Unable to execute query");
  };

  const clearData = () => {
    setTestData([]);
    setError(null);
    setIsLoading(false);
  };

  // Parse the backend response format
  const simulateBackendResponse = () => {
    // This simulates parsing the QUERY_RESULTS: marker from backend
    const backendResponse = {
      "type": "query_results",
      "data": [
        { "CDSCode": "01610176109835" },
        { "CDSCode": "01610176109843" },
        { "CDSCode": "01610176109850" },
        { "CDSCode": "01610176109868" },
        { "CDSCode": "01610176109876" }
      ],
      "row_count": 5
    };
    
    setTestData(backendResponse.data);
    setError(null);
  };

  return (
    <div className="container mx-auto p-8">
      <h1 className="text-2xl font-bold mb-6">DataTable Component Test</h1>
      
      <div className="mb-6 space-x-2">
        <Button onClick={loadTestData1}>Load Simple Data</Button>
        <Button onClick={loadTestData2}>Load Complex Data</Button>
        <Button onClick={loadTestData3}>Load 1000 Rows</Button>
        <Button onClick={simulateBackendResponse}>Simulate Backend Response</Button>
        <Button onClick={simulateLoading}>Simulate Loading</Button>
        <Button onClick={simulateError}>Simulate Error</Button>
        <Button onClick={clearData} variant="outline">Clear</Button>
      </div>

      <div className="mb-4">
        <p className="text-sm text-gray-600">
          Current data: {testData.length} rows | 
          Loading: {isLoading ? 'Yes' : 'No'} | 
          Error: {error ? 'Yes' : 'No'}
        </p>
        {testData.length > 0 && (
          <pre className="mt-2 p-2 bg-gray-100 rounded text-xs overflow-auto max-h-32">
            {JSON.stringify(testData.slice(0, 3), null, 2)}
          </pre>
        )}
      </div>

      <DataTable 
        data={testData}
        isLoading={isLoading}
        error={error}
      />
    </div>
  );
}