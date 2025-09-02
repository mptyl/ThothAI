// Copyright (c) 2025 Marco Pancotti
// This file is part of ThothAI and is released under the Apache License 2.0.
// See the LICENSE.md file in the project root for full license information.

import { getApiConfig } from './config';

interface ExecuteQueryRequest {
  workspace_id: number;
  sql: string;
  limit?: number;
}

interface ExecuteQueryResponse {
  success: boolean;
  data?: any[];
  error?: string;
  execution_time?: number;
  row_count?: number;
}

export async function executeQuery(
  workspaceId: number,
  sql: string,
  limit: number = 1000
): Promise<ExecuteQueryResponse> {
  const config = getApiConfig();
  
  try {
    const response = await fetch(`${config.djangoServer}/api/dbmanager/execute/`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-API-Key': config.djangoApiKey,
      },
      body: JSON.stringify({
        workspace_id: workspaceId,
        sql: sql,
        limit: limit,
      } as ExecuteQueryRequest),
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => null);
      throw new Error(
        errorData?.error || 
        errorData?.message || 
        `HTTP error! status: ${response.status}`
      );
    }

    const result = await response.json();
    
    return {
      success: true,
      data: result.data || result.results || [],
      execution_time: result.execution_time,
      row_count: result.row_count || (result.data?.length ?? 0),
    };
  } catch (error) {
    console.error('Query execution error:', error);
    return {
      success: false,
      error: error instanceof Error ? error.message : 'Failed to execute query',
    };
  }
}