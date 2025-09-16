// Copyright (c) 2025 Marco Pancotti
// This file is part of ThothAI and is released under the Apache License 2.0.
// See the LICENSE.md file in the project root for full license information.

import React, { useMemo, useState, useCallback, useEffect } from 'react';
import { OutputBlock } from '@/components/OutputBlock';
import { AgGridReact } from 'ag-grid-react';
import { 
  ColDef, 
  GridReadyEvent, 
  GridApi, 
  ModuleRegistry, 
  AllCommunityModule
} from 'ag-grid-community';
// Removed XLSX import - using CSV export instead
import 'ag-grid-community/styles/ag-grid.css';
import 'ag-grid-community/styles/ag-theme-alpine.css';
import { QueryExecutorAPI } from '../lib/api/query-executor';

// Register AG-Grid modules
ModuleRegistry.registerModules([AllCommunityModule]);

// Validate critical environment variables at component load
if (!process.env.NEXT_PUBLIC_SQL_GENERATOR_URL) {
  console.error('❌ FATAL: PaginatedDataTable cannot function without NEXT_PUBLIC_SQL_GENERATOR_URL');
  throw new Error('Missing required environment configuration for query execution');
}

interface PaginatedDataTableProps {
  sql: string;
  workspaceId: number;
  onError?: (error: string) => void;
  onDataLoaded?: (totalRows: number) => void;
}

export const PaginatedDataTable: React.FC<PaginatedDataTableProps> = ({ 
  sql, 
  workspaceId,
  onError,
  onDataLoaded 
}) => {
  const [gridApi, setGridApi] = useState<GridApi | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [totalRows, setTotalRows] = useState<number>(0);
  const [isInitialized, setIsInitialized] = useState<boolean>(false);
  const [columns, setColumns] = useState<string[]>([]);
  const [rowData, setRowData] = useState<any[]>([]);
  const [currentPage, setCurrentPage] = useState<number>(0);
  const [pageSize, setPageSize] = useState<number>(10);
  const [sortModel, setSortModel] = useState<any[]>([]);
  const [filterModel, setFilterModel] = useState<{[key: string]: string}>({});
  
  const queryExecutor = useMemo(() => new QueryExecutorAPI(), []);

  // Column definitions based on dynamic columns from the query
  const columnDefs = useMemo<ColDef[]>(() => {
    if (columns.length === 0) return [];

    const cols = columns.map(col => ({
      field: col,
      headerName: col,
      valueGetter: (params: any) => (params && params.data ? params.data[col] : undefined),
      filter: 'agTextColumnFilter', // Enable text filter
      sortable: true, // Enable sorting
      resizable: true,
      minWidth: 100,
      flex: 1,
      floatingFilter: true, // Show filter inputs below headers
      filterParams: {
        debounceMs: 500, // Debounce filter input
        suppressAndOrCondition: true, // Simplify filter UI
      },
    }));
    
    // Return columns without checkbox selection (read-only table)
    return cols;
  }, [columns]);

  const defaultColDef = useMemo<ColDef>(() => ({
    sortable: true,
    filter: true,
    resizable: true,
    floatingFilter: true,
  }), []);

  // Load data from server with sorting and filtering
  const loadData = useCallback(async (page: number, size: number, sort?: any[], filter?: any) => {
    try {
      setIsLoading(true);
      setError(null);
      
      
      // Fetch paginated data with sort and filter
      const response = await queryExecutor.executeQuery({
        workspace_id: workspaceId,
        sql: sql,
        page: page,
        page_size: size,
        sort_model: sort || sortModel,
        filter_model: filter || filterModel
      });
      
      
      if (response.error) {
        setError(response.error);
        if (onError) onError(response.error);
        setRowData([]);
      } else {
        // Resolve columns and normalize data for single-column/scalar results
        const rawData = response.data || [];
        let incomingColumns = (response.columns && response.columns.length > 0) ? response.columns : [];
        let normalizedData = rawData;
        // Normalize if backend returns primitives or single-item arrays
        if (rawData.length > 0 && (typeof rawData[0] !== 'object' || Array.isArray(rawData[0]))) {
          const colName = incomingColumns[0] || 'column_1';
          normalizedData = rawData.map((row: any) => Array.isArray(row) ? { [colName]: row[0] } : { [colName]: row });
        }
        // If columns are missing, derive from normalized data
        if (incomingColumns.length === 0 && normalizedData.length > 0) {
          incomingColumns = Object.keys(normalizedData[0]);
        }
        
        // Update columns if this is the first load
        if (columns.length === 0 && incomingColumns.length > 0) {
          setColumns(incomingColumns);
        }
        
        // Update total rows - use normalized data length if total_rows is 0 or undefined
        const actualTotalRows = response.total_rows || (normalizedData.length || 0);
        setTotalRows(actualTotalRows);
        if (onDataLoaded) onDataLoaded(actualTotalRows);
        
        // Update row data
        setRowData(normalizedData);
        setIsInitialized(true);
        
      }
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : 'Failed to load data';
      setError(errorMsg);
      if (onError) onError(errorMsg);
      setRowData([]);
    } finally {
      setIsLoading(false);
    }
  }, [sql, workspaceId, queryExecutor, columns, onError, onDataLoaded, sortModel, filterModel]);

  // Handle page change
  const onPageChange = useCallback((newPage: number) => {
    setCurrentPage(newPage);
    loadData(newPage, pageSize, sortModel, filterModel);
  }, [pageSize, loadData, sortModel, filterModel]);

  // Handle page size change
  const onPageSizeChange = useCallback((newPageSize: number) => {
    setPageSize(newPageSize);
    setCurrentPage(0); // Reset to first page
    loadData(0, newPageSize, sortModel, filterModel);
  }, [loadData, sortModel, filterModel]);

  // Handle sort change
  const onSortChanged = useCallback(() => {
    if (gridApi) {
      const columnState = gridApi.getColumnState();
      
      const newSortModel = columnState
        .filter(col => col.sort && col.colId !== '__selection__')  // Exclude selection column
        .map(col => ({
          colId: col.colId,
          sort: col.sort
        }));
      
      setSortModel(newSortModel);
      setCurrentPage(0); // Reset to first page on sort change
      loadData(0, pageSize, newSortModel, filterModel);
    }
  }, [gridApi, pageSize, filterModel, loadData]);

  // Handle filter change
  const onFilterChanged = useCallback(() => {
    if (gridApi) {
      const newFilterModel = gridApi.getFilterModel();
      setFilterModel(newFilterModel);
      setCurrentPage(0); // Reset to first page on filter change
      loadData(0, pageSize, sortModel, newFilterModel);
    }
  }, [gridApi, pageSize, sortModel, loadData]);

  const onGridReady = useCallback((params: GridReadyEvent) => {
    setGridApi(params.api);
  }, []);

  // Export to CSV - ALWAYS fetch ALL data from database with current filters and sorting
  const exportToCSV = useCallback(async () => {
    try {
      setIsLoading(true);
      
      // First, get the actual total count with current filters
      // We need to do a fresh query to get the real total with filters applied
      const countResponse = await queryExecutor.executeQuery({
        workspace_id: workspaceId,
        sql: sql,
        page: 0,
        page_size: 1,
        sort_model: sortModel,
        filter_model: filterModel
      });
      
      const actualTotalRows = countResponse.total_rows || 0;
      
      if (actualTotalRows === 0) {
        alert('No data to export with current filters');
        setIsLoading(false);
        return;
      }
      
      // Export all data (up to a maximum for performance)
      const maxExportRows = 10000;
      const exportPageSize = 100;  // Use 100 to match backend validation limit
      const rowsToExport = Math.min(actualTotalRows, maxExportRows);
      const pages = Math.max(1, Math.ceil(rowsToExport / exportPageSize)); // Ensure at least 1 page
      
      let allData: any[] = [];
      let columnsForExport = columns;
      
      // Fetch ALL data from database with current filters and sorting
      for (let page = 0; page < pages; page++) {
        const response = await queryExecutor.executeQuery({
          workspace_id: workspaceId,
          sql: sql,
          page: page,
          page_size: exportPageSize,
          sort_model: sortModel,    // Apply current sorting
          filter_model: filterModel  // Apply current filters
        });
        
        // Check for errors
        if (response.error) {
          alert(`Export failed: ${response.error}`);
          setIsLoading(false);
          return;
        }
        
        if (response.data && response.data.length > 0) {
          allData = [...allData, ...response.data];
          // Get columns from first successful response if not already set
          if (columnsForExport.length === 0 && response.columns.length > 0) {
            columnsForExport = response.columns;
          }
        }
      }
      
      if (allData.length === 0) {
        alert('No data was fetched for export');
        setIsLoading(false);
        return;
      }

      // Convert to CSV
      const csvContent = convertToCSV(allData, columnsForExport);
      
      // Create download link
      const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
      const link = document.createElement('a');
      const url = URL.createObjectURL(blob);
      const timestamp = new Date().toISOString().replace(/[:.]/g, '-').split('T')[0];
      
      link.setAttribute('href', url);
      link.setAttribute('download', `query_results_${timestamp}.csv`);
      link.style.visibility = 'hidden';
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      
      // Show success message
      if (actualTotalRows > maxExportRows) {
        alert(`Successfully exported ${maxExportRows.toLocaleString()} rows (maximum limit) of ${actualTotalRows.toLocaleString()} total rows with current filters and sorting`);
      }
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : 'Failed to export data';
      alert(`Export failed: ${errorMsg}`);
    } finally {
      setIsLoading(false);
    }
  }, [totalRows, rowData.length, workspaceId, sql, queryExecutor, columns, sortModel, filterModel]);

  // Helper function to convert data to CSV
  const convertToCSV = (data: any[], cols: string[]): string => {
    if (!data || data.length === 0) return '';
    
    // Headers
    const headers = cols.length > 0 ? cols : Object.keys(data[0]);
    const csvHeaders = headers.map(h => `"${h}"`).join(',');
    
    // Rows
    const csvRows = data.map(row => {
      return headers.map(header => {
        const value = row[header];
        // Escape quotes and wrap in quotes
        if (value === null || value === undefined) return '""';
        const escaped = String(value).replace(/"/g, '""');
        return `"${escaped}"`;
      }).join(',');
    });
    
    return [csvHeaders, ...csvRows].join('\n');
  };

  // Load initial data when component mounts or sql/workspace changes
  useEffect(() => {
    if (sql && workspaceId) {
      // Reset state for new query
      setColumns([]);
      setRowData([]);
      setTotalRows(0);
      setCurrentPage(0);
      setSortModel([]);
      setFilterModel({});
      // Load fresh data
      loadData(0, pageSize, [], {});
    }
  }, [sql, workspaceId]); // eslint-disable-line react-hooks/exhaustive-deps

  if (error) {
    return (
      <div className="bg-destructive/10 border border-destructive/20 rounded-lg p-4 mt-4">
        <div className="text-destructive font-semibold flex items-center gap-2">
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          Query Execution Error
        </div>
        <div className="text-destructive/90 mt-2">{error}</div>
      </div>
    );
  }

  // Check if this is a single value result (like COUNT, SUM, AVG, etc.)
  const isSingleValueResult = columns.length === 1 && rowData.length === 1;

  // Render single value result in a special way
  if (isSingleValueResult && rowData.length > 0) {
    const columnName = columns[0];
    const value = rowData[0][columnName];
    
    return (
      <div className="mt-2">
        <OutputBlock>
          <div className="flex items-center gap-2 mb-4">
            <h3 className="text-lg font-semibold text-foreground flex items-center gap-2">
              <svg className="w-5 h-5 text-primary" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 17v1a1 1 0 001 1h4a1 1 0 001-1v-1m3-2V8a2 2 0 00-2-2H8a2 2 0 00-2 2v7m3-2h6" />
              </svg>
              Query Result
            </h3>
          </div>
          
          {/* Single Value Display */}
          <div className="bg-card/50 border border-border/50 rounded-lg p-6">
            <div className="text-center">
              <div className="text-sm text-muted-foreground mb-2 uppercase tracking-wider">
                {columnName}
              </div>
              <div className="text-4xl font-bold text-primary">
                {value !== null && value !== undefined ? value.toLocaleString() : '0'}
              </div>
            </div>
          </div>
        </OutputBlock>
      </div>
    );
  }

  // Check if query was successful but returned no records
  if (isInitialized && !isLoading && !error && rowData.length === 0 && totalRows === 0) {
    return (
      <div className="mt-2">
        <OutputBlock>
          <div className="flex items-center gap-2 mb-4">
            <h3 className="text-lg font-semibold text-foreground flex items-center gap-2">
              <svg className="w-5 h-5 text-muted-foreground" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
              Query Executed Successfully
            </h3>
          </div>
          
          {/* No Results Message */}
          <div className="bg-amber-50 dark:bg-amber-950/30 border border-amber-200 dark:border-amber-800/50 rounded-lg p-6">
            <div className="flex items-start gap-3">
              <div className="flex-shrink-0">
                <svg className="w-6 h-6 text-amber-600 dark:text-amber-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
              </div>
              <div className="flex-1">
                <h4 className="text-lg font-medium text-amber-800 dark:text-amber-200 mb-2">
                  No Records Found
                </h4>
                <p className="text-amber-700 dark:text-amber-300 mb-3">
                  Your query was executed successfully, but no records match the specified criteria.
                </p>
                <div className="text-sm text-amber-600 dark:text-amber-400">
                  <p className="font-medium mb-1">Suggestions:</p>
                  <ul className="list-disc list-inside space-y-1 ml-2">
                    <li>Review and adjust your search filters</li>
                    <li>Check date ranges or numeric criteria</li>
                    <li>Try broadening your search parameters</li>
                    <li>Verify that the expected data exists in your database</li>
                  </ul>
                </div>
              </div>
            </div>
          </div>
        </OutputBlock>
      </div>
    );
  }

  return (
    <div className="mt-2">
      <OutputBlock>
        <div>
          <div className="flex justify-between items-center mb-4">
          <h3 className="text-lg font-semibold text-foreground flex items-center gap-2">
            <svg className="w-5 h-5 text-primary" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 17v1a1 1 0 001 1h4a1 1 0 001-1v-1m3-2V8a2 2 0 00-2-2H8a2 2 0 00-2 2v7m3-2h6" />
            </svg>
            Query Results
          {(totalRows > 0 || rowData.length > 0) && (
            <span className="text-sm font-normal text-muted-foreground ml-2">
              {(totalRows || rowData.length).toLocaleString()} {(totalRows || rowData.length) === 1 ? 'record' : 'records'} found
            </span>
          )}
          {Object.keys(filterModel).length > 0 && (
            <span className="text-xs px-2 py-1 bg-amber-500/10 text-amber-500 border border-amber-500/20 rounded-full">
              Filtered
            </span>
          )}
          {sortModel.length > 0 && (
            <span className="text-xs px-2 py-1 bg-blue-500/10 text-blue-500 border border-blue-500/20 rounded-full">
              Sorted
            </span>
          )}
        </h3>
        <button
          onClick={exportToCSV}
          disabled={isLoading || (rowData.length === 0 && isInitialized)}
          className="px-4 py-2 bg-primary/10 text-primary border border-primary/20 rounded-lg hover:bg-primary/20 hover:border-primary/30 transition-all duration-200 flex items-center gap-2 group disabled:opacity-50 disabled:cursor-not-allowed"
        >
          <svg 
            className="w-5 h-5 group-hover:scale-110 transition-transform" 
            fill="none" 
            stroke="currentColor" 
            viewBox="0 0 24 24"
          >
            <path 
              strokeLinecap="round" 
              strokeLinejoin="round" 
              strokeWidth={2} 
              d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" 
            />
          </svg>
          Export to CSV
        </button>
      </div>
      
      <div 
        className="ag-theme-alpine-dark rounded-lg overflow-hidden border border-border/50" 
        style={{ height: '400px', width: '100%' }}
      >
        <AgGridReact
          theme="legacy"
          columnDefs={columnDefs}
          defaultColDef={defaultColDef}
          rowData={rowData}
          onGridReady={onGridReady}
          onSortChanged={onSortChanged}
          onFilterChanged={onFilterChanged}
          animateRows={true}
          suppressCellFocus={true}
          suppressFieldDotNotation={true}
          pagination={false} // We'll handle pagination manually
          loading={isLoading}
          rowHeight={32} // Make rows less tall
          overlayLoadingTemplate={
            '<div class="flex items-center justify-center h-full"><div class="animate-spin rounded-full h-12 w-12 border-b-2 border-primary"></div></div>'
          }
          overlayNoRowsTemplate={
            '<div class="flex items-center justify-center h-full text-muted-foreground">No records found</div>'
          }
        />
      </div>
      
      {/* Custom Pagination Controls */}
      <div className="flex items-center justify-between mt-2 p-3 bg-background/50 rounded-lg border border-border/50">
        <div className="flex items-center gap-4">
          <label className="text-sm text-muted-foreground">
            Rows per page:
          </label>
          <select
            value={pageSize}
            onChange={(e) => onPageSizeChange(Number(e.target.value))}
            className="px-3 py-1 bg-background border border-border rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-primary/50"
            disabled={isLoading}
          >
            <option value="10">10</option>
            <option value="20">20</option>
            <option value="50">50</option>
            <option value="100">100</option>
          </select>
        </div>
        
        <div className="flex items-center gap-2">
          <button
            onClick={() => onPageChange(0)}
            disabled={currentPage === 0 || isLoading}
            className="p-2 rounded-md hover:bg-muted disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            title="First page"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 19l-7-7 7-7m8 14l-7-7 7-7" />
            </svg>
          </button>
          
          <button
            onClick={() => onPageChange(currentPage - 1)}
            disabled={currentPage === 0 || isLoading}
            className="p-2 rounded-md hover:bg-muted disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            title="Previous page"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
            </svg>
          </button>
          
          <span className="px-3 text-sm text-muted-foreground">
            {currentPage + 1} / {Math.max(1, Math.ceil((totalRows || rowData.length) / pageSize))}
          </span>
          
          <button
            onClick={() => onPageChange(currentPage + 1)}
            disabled={currentPage >= Math.max(0, Math.ceil((totalRows || rowData.length) / pageSize) - 1) || isLoading}
            className="p-2 rounded-md hover:bg-muted disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            title="Next page"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
            </svg>
          </button>
          
          <button
            onClick={() => onPageChange(Math.max(0, Math.ceil((totalRows || rowData.length) / pageSize) - 1))}
            disabled={currentPage >= Math.max(0, Math.ceil((totalRows || rowData.length) / pageSize) - 1) || isLoading}
            className="p-2 rounded-md hover:bg-muted disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            title="Last page"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 5l7 7-7 7M5 5l7 7-7 7" />
            </svg>
          </button>
        </div>
        
        <div className="text-sm text-muted-foreground">
          {rowData.length > 0 ? (
            <>Showing {Math.min((currentPage * pageSize) + 1, totalRows || rowData.length).toLocaleString()} - {Math.min((currentPage + 1) * pageSize, totalRows || rowData.length).toLocaleString()} of {(totalRows || rowData.length).toLocaleString()} records</>
          ) : isLoading ? (
            <>Loading...</>
          ) : isInitialized ? (
            <>No records to display</>
          ) : (
            <></>
          )}
        </div>
      </div>
        </div>
      </OutputBlock>
    </div>
  );
};