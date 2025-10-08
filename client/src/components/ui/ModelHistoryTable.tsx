/**
 * ModelHistoryTable Component
 *
 * Displays inference history for the logged-in user.
 */

import React, { useState } from "react";
import { Button, Alert, Typography, Card } from "designbricks";
import { Skeleton } from "@/components/ui/skeleton";
import { RefreshCw, ChevronLeft, ChevronRight } from "lucide-react";

interface InferenceLog {
  id: number;
  request_id: string;
  endpoint_name: string;
  user_id: string;
  inputs: Record<string, any>;
  predictions: Record<string, any> | null;
  status: "SUCCESS" | "ERROR" | "TIMEOUT";
  execution_time_ms: number | null;
  error_message: string | null;
  created_at: string | null;
  completed_at: string | null;
}

interface ModelHistoryTableProps {
  logs?: InferenceLog[];
  totalCount?: number;
  loading?: boolean;
  error?: string | null;
  onRefresh?: () => void;
  onPageChange?: (limit: number, offset: number) => void;
  currentLimit?: number;
  currentOffset?: number;
}

export const ModelHistoryTable: React.FC<ModelHistoryTableProps> = ({
  logs = [],
  totalCount = 0,
  loading = false,
  error = null,
  onRefresh,
  onPageChange,
  currentLimit = 50,
  currentOffset = 0,
}) => {
  const [expandedRow, setExpandedRow] = useState<number | null>(null);

  // Calculate pagination
  const currentPage = Math.floor(currentOffset / currentLimit) + 1;
  const totalPages = Math.ceil(totalCount / currentLimit);
  const hasNextPage = currentOffset + currentLimit < totalCount;
  const hasPrevPage = currentOffset > 0;

  const handleNextPage = () => {
    if (hasNextPage && onPageChange) {
      onPageChange(currentLimit, currentOffset + currentLimit);
    }
  };

  const handlePrevPage = () => {
    if (hasPrevPage && onPageChange) {
      onPageChange(currentLimit, Math.max(0, currentOffset - currentLimit));
    }
  };

  const toggleRowExpansion = (logId: number) => {
    setExpandedRow(expandedRow === logId ? null : logId);
  };

  const formatDate = (dateStr: string | null) => {
    if (!dateStr) return "N/A";
    try {
      const date = new Date(dateStr);
      return date.toLocaleString();
    } catch {
      return dateStr;
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case "SUCCESS":
        return "#10b981";
      case "ERROR":
        return "#ef4444";
      case "TIMEOUT":
        return "#f59e0b";
      default:
        return "#6b7280";
    }
  };

  // Loading state
  if (loading) {
    return (
      <div className="model-history-container space-y-4">
        <Skeleton className="h-12 w-full" />
        <Skeleton className="h-64 w-full" />
      </div>
    );
  }

  return (
    <div className="model-history-container">
      {/* Header */}
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          marginBottom: "16px",
        }}
      >
        <div>
          <Typography.Title level={2} withoutMargins>
            Inference History
          </Typography.Title>
          <Typography.Text color="secondary">
            View your past model inference requests
          </Typography.Text>
        </div>
        {onRefresh && (
          <Button
            variant="secondary"
            size="small"
            onClick={onRefresh}
            disabled={loading}
          >
            <RefreshCw className="h-4 w-4 mr-2" />
            Refresh
          </Button>
        )}
      </div>

      {/* Error Message */}
      {error && (
        <Alert severity="error" className="mb-4">
          {error}
        </Alert>
      )}

      {/* No logs available */}
      {logs.length === 0 && !loading && !error && (
        <Alert severity="info">
          No inference history found. Make a model inference request to see it
          here.
        </Alert>
      )}

      {/* Logs Table */}
      {logs.length > 0 && (
        <>
          <div
            style={{
              overflowX: "auto",
              border: "1px solid #e5e7eb",
              borderRadius: "8px",
            }}
          >
            <table
              style={{
                width: "100%",
                borderCollapse: "collapse",
                fontSize: "14px",
              }}
            >
              <thead style={{ backgroundColor: "#f9fafb" }}>
                <tr>
                  <th
                    style={{
                      padding: "12px",
                      textAlign: "left",
                      fontWeight: 600,
                      borderBottom: "1px solid #e5e7eb",
                    }}
                  >
                    Request ID
                  </th>
                  <th
                    style={{
                      padding: "12px",
                      textAlign: "left",
                      fontWeight: 600,
                      borderBottom: "1px solid #e5e7eb",
                    }}
                  >
                    Endpoint
                  </th>
                  <th
                    style={{
                      padding: "12px",
                      textAlign: "left",
                      fontWeight: 600,
                      borderBottom: "1px solid #e5e7eb",
                    }}
                  >
                    Status
                  </th>
                  <th
                    style={{
                      padding: "12px",
                      textAlign: "left",
                      fontWeight: 600,
                      borderBottom: "1px solid #e5e7eb",
                    }}
                  >
                    Time (ms)
                  </th>
                  <th
                    style={{
                      padding: "12px",
                      textAlign: "left",
                      fontWeight: 600,
                      borderBottom: "1px solid #e5e7eb",
                    }}
                  >
                    Created At
                  </th>
                  <th
                    style={{
                      padding: "12px",
                      textAlign: "left",
                      fontWeight: 600,
                      borderBottom: "1px solid #e5e7eb",
                    }}
                  >
                    Actions
                  </th>
                </tr>
              </thead>
              <tbody>
                {logs.map((log, index) => (
                  <React.Fragment key={log.id}>
                    <tr
                      style={{
                        backgroundColor: index % 2 === 0 ? "#ffffff" : "#f9fafb",
                        cursor: "pointer",
                      }}
                      onClick={() => toggleRowExpansion(log.id)}
                    >
                      <td
                        style={{
                          padding: "12px",
                          borderBottom: "1px solid #e5e7eb",
                        }}
                      >
                        <Typography.Text style={{ fontFamily: "monospace", fontSize: "12px" }}>
                          {log.request_id.substring(0, 20)}...
                        </Typography.Text>
                      </td>
                      <td
                        style={{
                          padding: "12px",
                          borderBottom: "1px solid #e5e7eb",
                        }}
                      >
                        <Typography.Text>{log.endpoint_name}</Typography.Text>
                      </td>
                      <td
                        style={{
                          padding: "12px",
                          borderBottom: "1px solid #e5e7eb",
                        }}
                      >
                        <span
                          style={{
                            display: "inline-block",
                            padding: "4px 8px",
                            borderRadius: "4px",
                            backgroundColor: `${getStatusColor(log.status)}20`,
                            color: getStatusColor(log.status),
                            fontWeight: 600,
                            fontSize: "12px",
                          }}
                        >
                          {log.status}
                        </span>
                      </td>
                      <td
                        style={{
                          padding: "12px",
                          borderBottom: "1px solid #e5e7eb",
                        }}
                      >
                        <Typography.Text>
                          {log.execution_time_ms !== null
                            ? log.execution_time_ms.toLocaleString()
                            : "N/A"}
                        </Typography.Text>
                      </td>
                      <td
                        style={{
                          padding: "12px",
                          borderBottom: "1px solid #e5e7eb",
                        }}
                      >
                        <Typography.Text>{formatDate(log.created_at)}</Typography.Text>
                      </td>
                      <td
                        style={{
                          padding: "12px",
                          borderBottom: "1px solid #e5e7eb",
                        }}
                      >
                        <Button
                          variant="secondary"
                          size="small"
                          onClick={(e) => {
                            e.stopPropagation();
                            toggleRowExpansion(log.id);
                          }}
                        >
                          {expandedRow === log.id ? "Hide" : "Details"}
                        </Button>
                      </td>
                    </tr>
                    {expandedRow === log.id && (
                      <tr>
                        <td
                          colSpan={6}
                          style={{
                            padding: "16px",
                            backgroundColor: "#f9fafb",
                            borderBottom: "1px solid #e5e7eb",
                          }}
                        >
                          <Card padding="small" className="space-y-4">
                            <div>
                              <Typography.Text bold style={{ display: "block", marginBottom: "8px" }}>
                                Request ID:
                              </Typography.Text>
                              <Typography.Text style={{ fontFamily: "monospace", fontSize: "12px" }}>
                                {log.request_id}
                              </Typography.Text>
                            </div>

                            <div>
                              <Typography.Text bold style={{ display: "block", marginBottom: "8px" }}>
                                Inputs:
                              </Typography.Text>
                              <pre
                                style={{
                                  margin: 0,
                                  padding: "12px",
                                  backgroundColor: "#ffffff",
                                  border: "1px solid #e5e7eb",
                                  borderRadius: "4px",
                                  fontSize: "12px",
                                  overflowX: "auto",
                                  maxHeight: "200px",
                                }}
                              >
                                {JSON.stringify(log.inputs, null, 2)}
                              </pre>
                            </div>

                            {log.status === "SUCCESS" && log.predictions && (
                              <div>
                                <Typography.Text bold style={{ display: "block", marginBottom: "8px" }}>
                                  Predictions:
                                </Typography.Text>
                                <pre
                                  style={{
                                    margin: 0,
                                    padding: "12px",
                                    backgroundColor: "#ffffff",
                                    border: "1px solid #e5e7eb",
                                    borderRadius: "4px",
                                    fontSize: "12px",
                                    overflowX: "auto",
                                    maxHeight: "200px",
                                  }}
                                >
                                  {JSON.stringify(log.predictions, null, 2)}
                                </pre>
                              </div>
                            )}

                            {log.error_message && (
                              <div>
                                <Typography.Text bold style={{ display: "block", marginBottom: "8px" }}>
                                  Error Message:
                                </Typography.Text>
                                <Alert severity="error">{log.error_message}</Alert>
                              </div>
                            )}

                            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "16px" }}>
                              <div>
                                <Typography.Text bold style={{ display: "block", marginBottom: "4px" }}>
                                  Created At:
                                </Typography.Text>
                                <Typography.Text color="secondary">
                                  {formatDate(log.created_at)}
                                </Typography.Text>
                              </div>
                              <div>
                                <Typography.Text bold style={{ display: "block", marginBottom: "4px" }}>
                                  Completed At:
                                </Typography.Text>
                                <Typography.Text color="secondary">
                                  {formatDate(log.completed_at)}
                                </Typography.Text>
                              </div>
                            </div>
                          </Card>
                        </td>
                      </tr>
                    )}
                  </React.Fragment>
                ))}
              </tbody>
            </table>
          </div>

          {/* Pagination */}
          {totalPages > 1 && (
            <div
              style={{
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
                marginTop: "16px",
              }}
            >
              <Typography.Text color="secondary">
                Showing {currentOffset + 1} to{" "}
                {Math.min(currentOffset + currentLimit, totalCount)} of {totalCount}{" "}
                logs
              </Typography.Text>
              <div style={{ display: "flex", gap: "8px" }}>
                <Button
                  variant="secondary"
                  size="small"
                  onClick={handlePrevPage}
                  disabled={!hasPrevPage}
                >
                  <ChevronLeft className="h-4 w-4 mr-1" />
                  Previous
                </Button>
                <Typography.Text
                  style={{
                    display: "flex",
                    alignItems: "center",
                    padding: "0 12px",
                  }}
                >
                  Page {currentPage} of {totalPages}
                </Typography.Text>
                <Button
                  variant="secondary"
                  size="small"
                  onClick={handleNextPage}
                  disabled={!hasNextPage}
                >
                  Next
                  <ChevronRight className="h-4 w-4 ml-1" />
                </Button>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
};

export default ModelHistoryTable;

