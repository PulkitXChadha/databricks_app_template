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
    <div className="w-full px-4 sm:px-6 lg:px-8 py-8">
      <MetricsDashboard />
    </div>
  );
};

export default MetricsPage;

