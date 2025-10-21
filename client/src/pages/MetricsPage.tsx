import React from 'react';
import { MetricsDashboard } from '../components/MetricsDashboard';

/**
 * Metrics Page - Dashboard for application performance and usage metrics
 * 
 * Accessible only to workspace administrators (FR-011).
 * Displays performance metrics, usage events, and endpoint analysis.
 */
export const MetricsPage: React.FC = () => {
  return (
    <div className="container mx-auto px-4 py-8">
      <MetricsDashboard />
    </div>
  );
};

export default MetricsPage;

