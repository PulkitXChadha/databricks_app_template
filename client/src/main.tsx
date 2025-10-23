import React from "react";
import ReactDOM from "react-dom/client";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import App from "./App.tsx";
import "designbricks/dist/styles/global.css";
import "./index.css";
import { OpenAPI } from "./fastapi_client";

// Configure API client for local development
// In production, Databricks automatically injects the X-Forwarded-Access-Token header
// For local development, we need to manually set it
const userToken = import.meta.env.VITE_DATABRICKS_USER_TOKEN;

if (userToken) {
  OpenAPI.HEADERS = {
    'X-Forwarded-Access-Token': userToken
  };
  console.log('✅ User token configured for local development');
} else {
  console.warn('⚠️  No user token found. API calls will fail.');
  console.warn('To fix: Create client/.env.local with VITE_DATABRICKS_USER_TOKEN');
  console.warn('Get token with: databricks auth token');
}

// Set base URL for API calls
// Use empty string for production (relative paths) or explicit URL for local dev
// In local development, set VITE_API_BASE_URL=http://localhost:8000 in client/.env.local
OpenAPI.BASE = import.meta.env.VITE_API_BASE_URL || '';

const queryClient = new QueryClient();

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <QueryClientProvider client={queryClient}>
      <App />
    </QueryClientProvider>
  </React.StrictMode>,
);
