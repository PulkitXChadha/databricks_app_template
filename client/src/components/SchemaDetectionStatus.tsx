/**
 * Schema Detection Status Badge Component
 * 
 * Displays detected model type with appropriate styling using Design Bricks Badge.
 */

import React from 'react';
import { EndpointType, DetectionStatus } from '../fastapi_client';

interface SchemaDetectionStatusProps {
  detectedType: EndpointType | string;
  status: DetectionStatus | string;
}

export function SchemaDetectionStatus({ detectedType, status }: SchemaDetectionStatusProps) {
  // Map endpoint type to user-friendly display text
  const getDisplayText = (): string => {
    if (status === 'TIMEOUT' || status === 'FAILURE') {
      return 'Unknown';
    }
    
    switch (detectedType) {
      case 'FOUNDATION_MODEL':
        return 'Foundation Model';
      case 'MLFLOW_MODEL':
        return 'MLflow Model';
      case 'UNKNOWN':
      default:
        return 'Unknown';
    }
  };
  
  // Map to badge color/variant
  const getVariant = (): string => {
    if (status === 'TIMEOUT' || status === 'FAILURE') {
      return 'warning';
    }
    
    switch (detectedType) {
      case 'FOUNDATION_MODEL':
        return 'success';
      case 'MLFLOW_MODEL':
        return 'info';
      case 'UNKNOWN':
      default:
        return 'default';
    }
  };
  
  return (
    <span 
      className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium badge-${getVariant()}`}
      style={{
        backgroundColor: getVariant() === 'success' ? '#10b981' : 
                        getVariant() === 'info' ? '#3b82f6' :
                        getVariant() === 'warning' ? '#f59e0b' : '#6b7280',
        color: 'white'
      }}
    >
      {getDisplayText()}
    </span>
  );
}

