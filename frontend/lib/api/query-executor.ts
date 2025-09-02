// Copyright (c) 2025 Marco Pancotti
// This file is part of ThothAI and is released under the Apache License 2.0.
// See the LICENSE.md file in the project root for full license information.

interface PaginationRequest {
  workspace_id: number;
  sql: string;
  page: number;
  page_size: number;
  sort_model?: any[];
  filter_model?: any;
}

interface PaginationResponse {
  data: any[];
  total_rows: number;
  page: number;
  page_size: number;
  has_next: boolean;
  has_previous: boolean;
  columns: string[];
  error?: string;
}

// Validate environment variable at module load time - fail fast
const SQL_GENERATOR_URL = process.env.NEXT_PUBLIC_SQL_GENERATOR_URL;
if (!SQL_GENERATOR_URL) {
  const errorMsg = `
    ⚠️ CRITICAL CONFIGURATION ERROR ⚠️
    
    NEXT_PUBLIC_SQL_GENERATOR_URL environment variable is NOT SET!
    
    The application cannot function without this configuration.
    Please ensure the .env.local file in the project root contains:
    NEXT_PUBLIC_SQL_GENERATOR_URL=http://localhost:8180
    
    Then restart the application.
  `;
  console.error(errorMsg);
  throw new Error('FATAL: NEXT_PUBLIC_SQL_GENERATOR_URL is required but not configured');
}

export class QueryExecutorAPI {
  private baseURL: string;
  private retryCount: number = 3;
  private retryDelay: number = 1000;

  constructor() {
    this.baseURL = SQL_GENERATOR_URL as string; // Type assertion since we've validated above
  }

  /**
   * Execute a paginated SQL query
   */
  async executeQuery(request: PaginationRequest): Promise<PaginationResponse> {
    const url = `${this.baseURL}/execute-query`;
    
    let lastError: Error | null = null;
    
    for (let attempt = 0; attempt < this.retryCount; attempt++) {
      try {
        const response = await fetch(url, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify(request),
        });

        if (!response.ok) {
          const errorText = await response.text();
          throw new Error(`HTTP ${response.status}: ${errorText}`);
        }

        const data: PaginationResponse = await response.json();
        return data;
        
      } catch (error) {
        lastError = error as Error;
        console.error(`Query execution attempt ${attempt + 1} failed:`, error);
        
        // If this isn't the last attempt, wait before retrying
        if (attempt < this.retryCount - 1) {
          await this.delay(this.retryDelay * (attempt + 1));
        }
      }
    }
    
    // If all retries failed, return an error response
    return {
      data: [],
      total_rows: 0,
      page: request.page,
      page_size: request.page_size,
      has_next: false,
      has_previous: false,
      columns: [],
      error: lastError?.message || 'Failed to execute query after multiple attempts'
    };
  }

  /**
   * Fetch a specific page of data
   */
  async fetchPage(params: {
    sql: string;
    workspaceId: number;
    startRow: number;
    endRow: number;
    sortModel?: any[];
    filterModel?: any;
  }): Promise<PaginationResponse> {
    const pageSize = params.endRow - params.startRow;
    const page = Math.floor(params.startRow / pageSize);
    
    return this.executeQuery({
      workspace_id: params.workspaceId,
      sql: params.sql,
      page: page,
      page_size: pageSize,
      sort_model: params.sortModel,
      filter_model: params.filterModel
    });
  }

  /**
   * Get query metadata (count, columns) without fetching all data
   */
  async getQueryMetadata(workspaceId: number, sql: string): Promise<{
    totalRows: number;
    columns: string[];
    error?: string;
  }> {
    // Fetch just the first row to get metadata
    const response = await this.executeQuery({
      workspace_id: workspaceId,
      sql: sql,
      page: 0,
      page_size: 1
    });
    
    return {
      totalRows: response.total_rows,
      columns: response.columns,
      error: response.error
    };
  }

  /**
   * Helper method to add delay for retries
   */
  private delay(ms: number): Promise<void> {
    return new Promise(resolve => setTimeout(resolve, ms));
  }

  /**
   * Get the base URL for debugging
   */
  getBaseURL(): string {
    return this.baseURL;
  }
}