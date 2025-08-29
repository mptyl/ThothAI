// Copyright (c) 2025 Marco Pancotti
// This file is part of ThothAI and is released under the Apache License 2.0.
// See the LICENSE.md file in the project root for full license information.

import React, { useMemo, useState, useCallback } from 'react';
import { AgGridReact } from 'ag-grid-react';
import { ColDef, GridReadyEvent, GridApi, ModuleRegistry, AllCommunityModule } from 'ag-grid-community';
import * as XLSX from 'xlsx';
import 'ag-grid-community/styles/ag-grid.css';
import 'ag-grid-community/styles/ag-theme-alpine.css';

// Register AG-Grid modules
ModuleRegistry.registerModules([AllCommunityModule]);

interface DataTableProps {
  data: any[];
  isLoading?: boolean;
  error?: string | null;
}

export const DataTable: React.FC<DataTableProps> = ({ data, isLoading, error }) => {
  const [gridApi, setGridApi] = useState<GridApi | null>(null);

  const columnDefs = useMemo<ColDef[]>(() => {
    if (!data || data.length === 0) return [];

    const firstRow = data[0];
    const numColumns = Object.keys(firstRow).length;
    
    return Object.keys(firstRow).map(key => ({
      field: key,
      headerName: key,
      filter: true,
      sortable: true,
      resizable: true,
      minWidth: 150,
      // Use auto width instead of flex to allow horizontal scrolling
      width: numColumns > 6 ? 200 : 250,
      floatingFilter: true,
    }));
  }, [data]);

  const defaultColDef = useMemo<ColDef>(() => ({
    sortable: true,
    filter: true,
    resizable: true,
    floatingFilter: true,
  }), []);

  const onGridReady = useCallback((params: GridReadyEvent) => {
    setGridApi(params.api);
  }, []);

  const exportToExcel = useCallback(() => {
    if (!gridApi) return;

    const rowData: any[] = [];
    gridApi.forEachNodeAfterFilterAndSort(node => {
      rowData.push(node.data);
    });

    if (rowData.length === 0) {
      alert('No data to export');
      return;
    }

    const worksheet = XLSX.utils.json_to_sheet(rowData);
    const workbook = XLSX.utils.book_new();
    XLSX.utils.book_append_sheet(workbook, worksheet, 'Query Results');

    const timestamp = new Date().toISOString().replace(/[:.]/g, '-').split('T')[0];
    XLSX.writeFile(workbook, `query_results_${timestamp}.xlsx`);
  }, [gridApi]);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64 bg-background/50 rounded-lg border border-border">
        <div className="flex flex-col items-center gap-3">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary"></div>
          <div className="text-muted-foreground">Executing query...</div>
        </div>
      </div>
    );
  }

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

  if (!data || data.length === 0) {
    return (
      <div className="bg-muted/50 border border-border rounded-lg p-4 mt-4">
        <div className="text-muted-foreground flex items-center gap-2">
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M20 13V6a2 2 0 00-2-2H6a2 2 0 00-2 2v7m16 0v5a2 2 0 01-2 2H6a2 2 0 01-2-2v-5m16 0h-2.586a1 1 0 00-.707.293l-2.414 2.414a1 1 0 01-.707.293h-3.172a1 1 0 01-.707-.293l-2.414-2.414A1 1 0 006.586 13H4" />
          </svg>
          No results found
        </div>
      </div>
    );
  }

  return (
    <div className="mt-6">
      <div className="flex items-start gap-3 p-4">
        {/* ThothAI Icon - Same positioning as message avatar */}
        <div className="flex-shrink-0 mt-1">
          <div className="w-16 h-16 rounded-full overflow-hidden flex items-center justify-center bg-background/10">
            <img 
              src="/dio-thoth-dx.png" 
              alt="ThothAI" 
              className="w-16 h-16 object-contain"
            />
          </div>
        </div>
        
        {/* Table Container */}
        <div className="flex-1 min-w-0">
          <div className="flex justify-between items-center mb-4">
          <h3 className="text-lg font-semibold text-foreground flex items-center gap-2">
            <svg className="w-5 h-5 text-primary" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 17v1a1 1 0 001 1h4a1 1 0 001-1v-1m3-2V8a2 2 0 00-2-2H8a2 2 0 00-2 2v7m3-2h6" />
            </svg>
            Query Results 
            <span className="text-sm font-normal text-muted-foreground">({data.length} rows)</span>
          </h3>
          <button
            onClick={exportToExcel}
            className="px-4 py-2 bg-primary/10 text-primary border border-primary/20 rounded-lg hover:bg-primary/20 hover:border-primary/30 transition-all duration-200 flex items-center gap-2 group"
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
            Export to Excel
          </button>
        </div>
        
        <div 
          className="ag-theme-alpine-dark rounded-lg overflow-auto border border-border/50" 
          style={{ height: '500px', width: '100%' }}
        >
        <AgGridReact
          theme="legacy"
          rowData={data}
          columnDefs={columnDefs}
          defaultColDef={defaultColDef}
          pagination={true}
          paginationPageSize={20}
          paginationPageSizeSelector={[10, 20, 50, 100]}
          onGridReady={onGridReady}
          animateRows={true}
          suppressCellFocus={true}
          suppressHorizontalScroll={false}
          alwaysShowHorizontalScroll={true}
          overlayLoadingTemplate={
            '<div class="flex items-center justify-center h-full"><div class="animate-spin rounded-full h-12 w-12 border-b-2 border-primary"></div></div>'
          }
          overlayNoRowsTemplate={
            '<div class="flex items-center justify-center h-full text-muted-foreground">No data to display</div>'
          }
        />
      </div>
        </div>
      </div>
    </div>
  );
};