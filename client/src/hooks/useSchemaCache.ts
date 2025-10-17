/**
 * React hook for browser session storage caching of schema detection results
 * 
 * Uses sessionStorage API for automatic cleanup on tab close.
 * Cache persists for entire browser session until tab/window closes.
 */

import { SchemaDetectionResult } from '../fastapi_client';

export function useSchemaCache() {
  /**
   * Retrieve cached schema for an endpoint from sessionStorage
   */
  const getCachedSchema = (endpointName: string): SchemaDetectionResult | null => {
    try {
      const cached = sessionStorage.getItem(`schema_${endpointName}`);
      return cached ? JSON.parse(cached) : null;
    } catch (error) {
      console.warn('Failed to retrieve cached schema:', error);
      return null;
    }
  };
  
  /**
   * Store schema detection result in sessionStorage
   */
  const setCachedSchema = (endpointName: string, schema: SchemaDetectionResult): void => {
    try {
      sessionStorage.setItem(`schema_${endpointName}`, JSON.stringify(schema));
    } catch (error) {
      console.warn('Failed to cache schema:', error);
    }
  };
  
  /**
   * Clear cached schema for a specific endpoint
   */
  const clearCachedSchema = (endpointName: string): void => {
    try {
      sessionStorage.removeItem(`schema_${endpointName}`);
    } catch (error) {
      console.warn('Failed to clear cached schema:', error);
    }
  };
  
  /**
   * Clear all cached schemas
   */
  const clearAllCachedSchemas = (): void => {
    try {
      const keys = Object.keys(sessionStorage);
      keys.forEach(key => {
        if (key.startsWith('schema_')) {
          sessionStorage.removeItem(key);
        }
      });
    } catch (error) {
      console.warn('Failed to clear all cached schemas:', error);
    }
  };
  
  return {
    getCachedSchema,
    setCachedSchema,
    clearCachedSchema,
    clearAllCachedSchemas
  };
}

