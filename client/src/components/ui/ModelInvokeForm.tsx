/**
 * ModelInvokeForm Component
 *
 * Form for invoking Model Serving endpoints for ML inference.
 * Includes automatic schema detection for foundation and MLflow models.
 */

import React, { useState, useEffect } from "react";
import { Button, Alert, TextField, Select, Typography } from "designbricks";
import { Skeleton } from "@/components/ui/skeleton";
import { SchemaDetectionStatus } from "@/components/SchemaDetectionStatus";
import { useSchemaCache } from "@/hooks/useSchemaCache";
import { ModelServingService, type SchemaDetectionResult } from "@/fastapi_client";

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
  
  // Schema detection state (T017)
  const [schemaDetecting, setSchemaDetecting] = useState(false);
  const [schemaResult, setSchemaResult] = useState<SchemaDetectionResult | null>(null);
  const { getCachedSchema, setCachedSchema } = useSchemaCache();

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

  const handleEndpointChange = async (value: string | number | (string | number)[]) => {
    const endpointName = value as string;
    setSelectedEndpoint(endpointName);
    setResponse(null);
    setInvocationError(null);
    
    // Trigger schema detection (T018)
    if (endpointName) {
      await detectSchema(endpointName);
    } else {
      setSchemaResult(null);
    }
  };
  
  // Schema detection function (T017)
  const detectSchema = async (endpointName: string) => {
    try {
      setSchemaDetecting(true);
      setSchemaResult(null);
      
      // Check cache first
      const cached = getCachedSchema(endpointName);
      if (cached) {
        setSchemaResult(cached);
        setInputsJson(JSON.stringify(cached.example_json, null, 2));
        setSchemaDetecting(false);
        return;
      }
      
      // Call API
      const result = await ModelServingService.detectEndpointSchemaApiModelServingEndpointsEndpointNameSchemaGet(
        endpointName
      );
      
      // Cache successful result
      if (result.status === 'SUCCESS') {
        setCachedSchema(endpointName, result);
      }
      
      setSchemaResult(result);
      
      // Auto-populate JSON input with example
      setInputsJson(JSON.stringify(result.example_json, null, 2));
      
    } catch (err: any) {
      console.warn('Schema detection failed:', err);
      // Don't show error to user - graceful degradation
      // User can still manually edit JSON
      setSchemaResult(null);
    } finally {
      setSchemaDetecting(false);
    }
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

  // Convert endpoints to Select options
  const endpointOptions = endpoints.map((ep) => ({
    value: ep.endpoint_name,
    label: `${ep.endpoint_name} (${ep.model_name} v${ep.model_version}) - ${ep.state}`,
  }));

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
        <Typography.Title level={2} withoutMargins style={{ marginBottom: "8px" }}>
          Model Serving Inference
        </Typography.Title>
        <Typography.Text color="secondary">
          Invoke ML models deployed to Databricks Model Serving endpoints
        </Typography.Text>
      </div>

      {/* Error Message */}
      {error && (
        <Alert severity="error" className="mb-4">
          {error}
        </Alert>
      )}

      {/* No endpoints available */}
      {endpoints.length === 0 && !loading && (
        <Alert severity="info" className="mb-4">
          No Model Serving endpoints available. Please create an endpoint
          first.
        </Alert>
      )}

      {/* Endpoint Selector */}
      <div style={{ marginBottom: "24px" }}>
        <div
          style={{
            display: "flex",
            justifyContent: "flex-end",
            alignItems: "center",
            marginBottom: "8px",
          }}
        >
          {onRefreshEndpoints && (
            <Button variant="primary" size="small" onClick={onRefreshEndpoints}>
              Refresh Endpoints
            </Button>
          )}
        </div>
        <Select
          options={endpointOptions}
          value={selectedEndpoint}
          onChange={handleEndpointChange}
          placeholder="-- Select an endpoint --"
          label="Select Endpoint"
          fullWidth
          searchable
          clearable
        />
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
          <Typography.Title level={3} withoutMargins style={{ marginBottom: "8px", fontSize: "14px" }}>
            Endpoint Details
          </Typography.Title>
          <div style={{ fontSize: "13px", color: "#666" }}>
            <div>
              <Typography.Text bold>Model:</Typography.Text> <Typography.Text>{currentEndpoint.model_name}</Typography.Text>
            </div>
            <div>
              <Typography.Text bold>Version:</Typography.Text> <Typography.Text>{currentEndpoint.model_version || "N/A"}</Typography.Text>
            </div>
            <div>
              <Typography.Text bold>State:</Typography.Text>{" "}
              <Typography.Text
                color={
                  currentEndpoint.state === "READY"
                    ? "success"
                    : currentEndpoint.state === "FAILED"
                      ? "error"
                      : "warning"
                }
              >
                {currentEndpoint.state}
              </Typography.Text>
            </div>
          </div>
          {currentEndpoint.state !== "READY" && (
            <Alert severity="warning" className="mt-2">
              Endpoint must be in READY state for inference
            </Alert>
          )}
        </div>
      )}

      {/* Input JSON Editor with Schema Detection (T018) */}
      <div style={{ marginBottom: "24px" }}>
        <div style={{ display: "flex", alignItems: "center", gap: "12px", marginBottom: "8px" }}>
          <Typography.Text bold>
            Input Data (JSON)
          </Typography.Text>
          {schemaResult && (
            <SchemaDetectionStatus 
              detectedType={schemaResult.detected_type} 
              status={schemaResult.status}
            />
          )}
          {schemaDetecting && (
            <Typography.Text color="secondary" style={{ fontSize: "13px" }}>
              Detecting schema...
            </Typography.Text>
          )}
        </div>
        
        {schemaDetecting ? (
          <Skeleton className="h-64 w-full" />
        ) : (
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
        )}
        
        {schemaResult?.status === 'TIMEOUT' && (
          <Alert severity="warning" className="mt-2">
            Schema detection timed out. You can manually edit the input format.
          </Alert>
        )}
        
        {schemaResult?.status === 'FAILURE' && (
          <Alert severity="warning" className="mt-2">
            Schema detection unavailable. Please consult model documentation for input format.
          </Alert>
        )}
        
        {schemaResult?.status === 'SUCCESS' && (
          <Typography.Hint style={{ marginTop: "4px" }}>
            Auto-detected {schemaResult.detected_type === 'FOUNDATION_MODEL' ? 'foundation model' : 'MLflow model'} schema. You can edit the JSON above.
          </Typography.Hint>
        )}
        
        {!schemaResult && !schemaDetecting && (
          <Typography.Hint style={{ marginTop: "4px" }}>
            Enter input data in JSON format. For chat models like Claude, use: {`{"messages": [{"role": "user", "content": "..."}], "max_tokens": 150}`}
          </Typography.Hint>
        )}
      </div>

      {/* Timeout Setting */}
      <div style={{ marginBottom: "24px" }}>
        <TextField
          id="timeout-input"
          type="number"
          label="Timeout (seconds)"
          description="Request timeout (1-300 seconds)"
          value={timeout.toString()}
          onChange={handleTimeoutChange}
          min={1}
          max={300}
          fullWidth
        />
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
        <Alert severity="error" className="mb-4">
          {invocationError}
        </Alert>
      )}

      {/* Response Display */}
      {response && (
        <div style={{ marginTop: "24px" }}>
          <Typography.Title level={3} withoutMargins style={{ marginBottom: "12px" }}>
            Inference Response
          </Typography.Title>

          {response.status === "SUCCESS" ? (
            <div
              style={{
                padding: "16px",
                backgroundColor: "#f0f9ff",
                borderRadius: "4px",
                border: "1px solid #bfdbfe",
              }}
            >
              <Alert severity="success" className="mb-3">
                Inference completed in {response.execution_time_ms}ms
              </Alert>

              <div style={{ marginBottom: "8px" }}>
                <Typography.Text bold>Request ID:</Typography.Text> <Typography.Text>{response.request_id}</Typography.Text>
              </div>

              <div style={{ marginBottom: "8px" }}>
                <Typography.Text bold>Predictions:</Typography.Text>
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
              <Alert severity="error">
                Inference {response.status}:{" "}
                {response.error_message || "Unknown error"}
              </Alert>
              <div style={{ marginTop: "12px" }}>
                <Typography.Text bold>Request ID:</Typography.Text> <Typography.Text>{response.request_id}</Typography.Text>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default ModelInvokeForm;
