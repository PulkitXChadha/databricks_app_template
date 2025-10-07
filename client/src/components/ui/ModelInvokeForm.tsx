/**
 * ModelInvokeForm Component
 *
 * Form for invoking Model Serving endpoints for ML inference.
 */

import React, { useState } from "react";
import { Button } from "designbricks";
import { Skeleton } from "@/components/ui/skeleton";
import { Alert, AlertDescription } from "@/components/ui/alert";

interface ModelEndpoint {
  endpoint_name: string;
  endpoint_id?: string;
  model_name: string;
  model_version?: string;
  state: "CREATING" | "READY" | "UPDATING" | "FAILED";
  workload_url?: string;
  creation_timestamp?: string;
  last_updated_timestamp?: string;
}

interface ModelInferenceResponse {
  request_id: string;
  endpoint_name: string;
  predictions?: Record<string, any>;
  status: "SUCCESS" | "ERROR" | "TIMEOUT";
  execution_time_ms: number;
  error_message?: string | null;
  completed_at?: string;
}

interface ModelInvokeFormProps {
  endpoints?: ModelEndpoint[];
  loading?: boolean;
  error?: string | null;
  onInvoke?: (
    endpointName: string,
    inputs: Record<string, any>,
    timeout: number,
  ) => Promise<ModelInferenceResponse>;
  onRefreshEndpoints?: () => void;
}

export const ModelInvokeForm: React.FC<ModelInvokeFormProps> = ({
  endpoints = [],
  loading = false,
  error = null,
  onInvoke,
  onRefreshEndpoints,
}) => {
  const [selectedEndpoint, setSelectedEndpoint] = useState<string>("");
  const [inputsJson, setInputsJson] = useState(
    '{\n  "messages": [{"role": "user", "content": "Hello! How are you?"}],\n  "max_tokens": 150\n}',
  );
  const [timeout, setTimeout] = useState(30);
  const [invoking, setInvoking] = useState(false);
  const [response, setResponse] = useState<ModelInferenceResponse | null>(null);
  const [invocationError, setInvocationError] = useState<string | null>(null);

  const handleInvoke = async () => {
    if (!onInvoke || !selectedEndpoint) return;

    try {
      setInvoking(true);
      setInvocationError(null);
      setResponse(null);

      // Parse and validate JSON
      const parsedInputs = JSON.parse(inputsJson);

      const result = await onInvoke(selectedEndpoint, parsedInputs, timeout);
      setResponse(result);
    } catch (err: any) {
      setInvocationError(err.message || "Failed to invoke model");
      console.error("Failed to invoke model:", err);
    } finally {
      setInvoking(false);
    }
  };

  const handleEndpointChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    setSelectedEndpoint(e.target.value);
    setResponse(null);
    setInvocationError(null);
  };

  const handleTimeoutChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const value = parseInt(e.target.value, 10);
    if (value >= 1 && value <= 300) {
      setTimeout(value);
    }
  };

  // Get selected endpoint details
  const currentEndpoint = endpoints.find(
    (ep) => ep.endpoint_name === selectedEndpoint,
  );

  // Loading state
  if (loading) {
    return (
      <div className="model-invoke-form-container space-y-4">
        <Skeleton className="h-12 w-full" />
        <Skeleton className="h-32 w-full" />
        <Skeleton className="h-64 w-full" />
      </div>
    );
  }

  return (
    <div
      className="model-invoke-form-container"
      style={{ maxWidth: "900px", margin: "0 auto" }}
    >
      {/* Header */}
      <div style={{ marginBottom: "24px" }}>
        <h2 style={{ margin: "0 0 8px 0" }}>Model Serving Inference</h2>
        <p style={{ margin: 0, fontSize: "14px", color: "#666" }}>
          Invoke ML models deployed to Databricks Model Serving endpoints
        </p>
      </div>

      {/* Error Message */}
      {error && (
        <Alert variant="destructive" className="mb-4">
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      {/* No endpoints available */}
      {endpoints.length === 0 && !loading && (
        <Alert className="mb-4">
          <AlertDescription>
            No Model Serving endpoints available. Please create an endpoint
            first.
          </AlertDescription>
        </Alert>
      )}

      {/* Endpoint Selector */}
      <div style={{ marginBottom: "24px" }}>
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            marginBottom: "8px",
          }}
        >
          <label htmlFor="endpoint-selector" style={{ fontWeight: 600 }}>
            Select Endpoint
          </label>
          {onRefreshEndpoints && (
            <Button variant="secondary" size="small" onClick={onRefreshEndpoints}>
              Refresh Endpoints
            </Button>
          )}
        </div>
        <select
          id="endpoint-selector"
          value={selectedEndpoint}
          onChange={handleEndpointChange}
          style={{
            width: "100%",
            padding: "10px 12px",
            fontSize: "14px",
            borderRadius: "4px",
            border: "1px solid #ddd",
            backgroundColor: "#fff",
          }}
        >
          <option value="">-- Select an endpoint --</option>
          {endpoints.map((ep) => (
            <option key={ep.endpoint_name} value={ep.endpoint_name}>
              {ep.endpoint_name} ({ep.model_name} v{ep.model_version}) -{" "}
              {ep.state}
            </option>
          ))}
        </select>
      </div>

      {/* Endpoint Details */}
      {currentEndpoint && (
        <div
          style={{
            marginBottom: "24px",
            padding: "12px",
            backgroundColor: "#f9f9f9",
            borderRadius: "4px",
          }}
        >
          <h3
            style={{ margin: "0 0 8px 0", fontSize: "14px", fontWeight: 600 }}
          >
            Endpoint Details
          </h3>
          <div style={{ fontSize: "13px", color: "#666" }}>
            <div>
              <strong>Model:</strong> {currentEndpoint.model_name}
            </div>
            <div>
              <strong>Version:</strong> {currentEndpoint.model_version || "N/A"}
            </div>
            <div>
              <strong>State:</strong>{" "}
              <span
                style={{
                  color:
                    currentEndpoint.state === "READY"
                      ? "green"
                      : currentEndpoint.state === "FAILED"
                        ? "red"
                        : "orange",
                }}
              >
                {currentEndpoint.state}
              </span>
            </div>
          </div>
          {currentEndpoint.state !== "READY" && (
            <Alert className="mt-2">
              <AlertDescription>
                Endpoint must be in READY state for inference
              </AlertDescription>
            </Alert>
          )}
        </div>
      )}

      {/* Input JSON Editor */}
      <div style={{ marginBottom: "24px" }}>
        <label
          htmlFor="inputs-json"
          style={{ display: "block", marginBottom: "8px", fontWeight: 600 }}
        >
          Input Data (JSON)
        </label>
        <textarea
          id="inputs-json"
          value={inputsJson}
          onChange={(e) => setInputsJson(e.target.value)}
          rows={10}
          style={{
            width: "100%",
            padding: "12px",
            fontSize: "14px",
            fontFamily: "monospace",
            borderRadius: "4px",
            border: "1px solid #ddd",
            backgroundColor: "#fafafa",
          }}
          placeholder='{"messages": [{"role": "user", "content": "Your question here"}], "max_tokens": 150}'
        />
        <p style={{ marginTop: "4px", fontSize: "12px", color: "#666" }}>
          Enter input data in JSON format. For chat models like Claude, use: {`{"messages": [{"role": "user", "content": "..."}], "max_tokens": 150}`}
        </p>
      </div>

      {/* Timeout Setting */}
      <div style={{ marginBottom: "24px" }}>
        <label
          htmlFor="timeout-input"
          style={{ display: "block", marginBottom: "8px", fontWeight: 600 }}
        >
          Timeout (seconds)
        </label>
        <input
          id="timeout-input"
          type="number"
          value={timeout}
          onChange={handleTimeoutChange}
          min={1}
          max={300}
          style={{
            width: "100%",
            padding: "10px 12px",
            fontSize: "14px",
            borderRadius: "4px",
            border: "1px solid #ddd",
          }}
        />
        <p style={{ marginTop: "4px", fontSize: "12px", color: "#666" }}>
          Request timeout (1-300 seconds)
        </p>
      </div>

      {/* Invoke Button */}
      <div style={{ marginBottom: "24px" }}>
        <Button
          variant="primary"
          onClick={handleInvoke}
          disabled={
            invoking || !selectedEndpoint || currentEndpoint?.state !== "READY"
          }
          loading={invoking}
        >
          Invoke Model
        </Button>
      </div>

      {/* Invocation Error */}
      {invocationError && (
        <Alert variant="destructive" className="mb-4">
          <AlertDescription>{invocationError}</AlertDescription>
        </Alert>
      )}

      {/* Response Display */}
      {response && (
        <div style={{ marginTop: "24px" }}>
          <h3 style={{ margin: "0 0 12px 0", fontSize: "16px" }}>
            Inference Response
          </h3>

          {response.status === "SUCCESS" ? (
            <div
              style={{
                padding: "16px",
                backgroundColor: "#f0f9ff",
                borderRadius: "4px",
                border: "1px solid #bfdbfe",
              }}
            >
              <Alert className="mb-3">
                <AlertDescription>
                  Inference completed in {response.execution_time_ms}ms
                </AlertDescription>
              </Alert>

              <div style={{ marginBottom: "8px", fontSize: "14px" }}>
                <strong>Request ID:</strong> {response.request_id}
              </div>

              <div style={{ marginBottom: "8px", fontSize: "14px" }}>
                <strong>Predictions:</strong>
              </div>
              <pre
                style={{
                  margin: 0,
                  padding: "12px",
                  backgroundColor: "#fff",
                  border: "1px solid #ddd",
                  borderRadius: "4px",
                  fontSize: "13px",
                  overflowX: "auto",
                }}
              >
                {JSON.stringify(response.predictions, null, 2)}
              </pre>
            </div>
          ) : (
            <div
              style={{
                padding: "16px",
                backgroundColor: "#fef2f2",
                borderRadius: "4px",
                border: "1px solid #fecaca",
              }}
            >
              <Alert variant="destructive">
                <AlertDescription>
                  Inference {response.status}:{" "}
                  {response.error_message || "Unknown error"}
                </AlertDescription>
              </Alert>
              <div style={{ marginTop: "12px", fontSize: "14px" }}>
                <strong>Request ID:</strong> {response.request_id}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default ModelInvokeForm;
