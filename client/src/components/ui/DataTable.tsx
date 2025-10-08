/**
 * DataTable Component
 *
 * Displays Unity Catalog query results with pagination controls.
 * Uses DesignBricks Table component for data display.
 */

import React, { useState, useEffect } from "react";
import { Button, Alert, Table, Typography, type Column as DBColumn } from "designbricks";
import { Skeleton } from "@/components/ui/skeleton";

interface Column {
  name: string;
  data_type: string;
  nullable: boolean;
}

interface DataTableProps {
  catalog: string;
  schema: string;
  table: string;
  columns?: Column[];
  data?: Record<string, any>[];
  totalRows?: number;
  loading?: boolean;
  error?: string | null;
  onPageChange?: (limit: number, offset: number) => void;
}

export const DataTable: React.FC<DataTableProps> = ({
  catalog,
  schema,
  table,
  columns = [],
  data = [],
  totalRows = 0,
  loading = false,
  error = null,
  onPageChange,
}) => {
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize, setPageSize] = useState(100);

  const totalPages = Math.ceil(totalRows / pageSize);
  const offset = (currentPage - 1) * pageSize;

  useEffect(() => {
    if (onPageChange) {
      onPageChange(pageSize, offset);
    }
  }, [currentPage, pageSize]);

  const handlePrevPage = () => {
    if (currentPage > 1) {
      setCurrentPage(currentPage - 1);
    }
  };

  const handleNextPage = () => {
    if (currentPage < totalPages) {
      setCurrentPage(currentPage + 1);
    }
  };

  const handlePageSizeChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    setPageSize(Number(e.target.value));
    setCurrentPage(1); // Reset to first page when changing page size
  };

  // Error state
  if (error) {
    return (
      <div className="data-table-container">
        <Alert severity="error">
          {error}
        </Alert>
      </div>
    );
  }

  // Loading state
  if (loading) {
    return (
      <div className="data-table-container space-y-4">
        <Skeleton className="h-12 w-full" />
        <Skeleton className="h-64 w-full" />
        <Skeleton className="h-12 w-full" />
      </div>
    );
  }

  // No data state
  if (data.length === 0) {
    return (
      <div className="data-table-container">
        <Alert severity="info">
          No data available in {catalog}.{schema}.{table}
        </Alert>
      </div>
    );
  }

  // Convert Unity Catalog columns to DesignBricks Table columns
  const tableColumns: DBColumn[] = columns.map((col) => ({
    key: col.name,
    header: (
      <>
        {col.name}
        <Typography.Text size="sm" color="secondary" style={{ marginLeft: "4px" }}>
          ({col.data_type})
        </Typography.Text>
      </>
    ),
    align: "left" as const,
    render: (value: any) => {
      if (value !== null && value !== undefined) {
        return String(value);
      }
      return <Typography.Text color="disabled" style={{ fontStyle: "italic" }}>NULL</Typography.Text>;
    },
  }));

  return (
    <div className="data-table-container">
      {/* Table Header */}
      <div className="table-header" style={{ marginBottom: "16px" }}>
        <Typography.Title level={3} withoutMargins>
          {catalog}.{schema}.{table}
        </Typography.Title>
        <Typography.Text size="sm" color="secondary" style={{ marginTop: "4px" }}>
          Showing {offset + 1} - {Math.min(offset + pageSize, totalRows)} of{" "}
          {totalRows} rows
        </Typography.Text>
      </div>

      {/* DesignBricks Table */}
      <div style={{ marginBottom: "16px" }}>
        <Table
          columns={tableColumns}
          data={data}
          striped
          hoverable
          bordered
          loading={loading}
          emptyMessage={`No data available in ${catalog}.${schema}.${table}`}
        />
      </div>

      {/* Pagination Controls */}
      <div
        className="pagination-controls"
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          padding: "12px",
          backgroundColor: "#f9f9f9",
          borderRadius: "4px",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
          <Typography.Text size="sm" style={{ marginRight: "8px" }}>
            Rows per page:
          </Typography.Text>
          <select
            id="page-size"
            value={pageSize}
            onChange={handlePageSizeChange}
            style={{
              padding: "6px 12px",
              fontSize: "14px",
              borderRadius: "4px",
              border: "1px solid #ddd",
              backgroundColor: "#fff",
              color: "#000",
            }}
          >
            <option value="10">10</option>
            <option value="25">25</option>
            <option value="50">50</option>
            <option value="100">100</option>
            <option value="500">500</option>
          </select>
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
          <Typography.Text size="sm">
            Page {currentPage} of {totalPages}
          </Typography.Text>

          <div style={{ display: "flex", gap: "8px" }}>
            <Button
              variant="secondary"
              size="small"
              disabled={currentPage === 1}
              onClick={handlePrevPage}
            >
              Previous
            </Button>

            <Button
              variant="secondary"
              size="small"
              disabled={currentPage === totalPages}
              onClick={handleNextPage}
            >
              Next
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default DataTable;
