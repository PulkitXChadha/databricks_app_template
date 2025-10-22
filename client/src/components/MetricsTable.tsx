import React from 'react';
import { Card, Typography, colors } from 'designbricks';

interface MetricsTableProps {
  performanceData: any;
  usageData: any;
}

interface MetricCardProps {
  title: string;
  value: string | number;
  description: string;
  valueColor?: string;
}

const MetricCard: React.FC<MetricCardProps> = ({ title, value, description, valueColor }) => {
  return (
    <Card padding="medium" className="h-full">
      <div className="flex flex-col space-y-2">
        <Typography.Text color="secondary" style={{ fontSize: '0.875rem', textTransform: 'uppercase', fontWeight: 500 }}>
          {title}
        </Typography.Text>
        <Typography.Title 
          level={2} 
          withoutMargins 
          style={{ color: valueColor || undefined }}
        >
          {value}
        </Typography.Title>
        <Typography.Text color="secondary" style={{ fontSize: '0.875rem' }}>
          {description}
        </Typography.Text>
      </div>
    </Card>
  );
};

export const MetricsTable: React.FC<MetricsTableProps> = ({ performanceData, usageData }) => {
  // Calculate active users from both performance and usage data
  const activeUsers = usageData?.metrics?.active_users || 0;
  const totalRequests = performanceData?.metrics?.total_requests || 0;
  const avgResponseTime = performanceData?.metrics?.avg_response_time_ms || 0;
  const errorRate = performanceData?.metrics?.error_rate || 0;
  const totalEvents = usageData?.metrics?.total_events || 0;
  const uniqueUsers = usageData?.metrics?.unique_users || 0;

  return (
    <div>
      <Typography.Title level={2} style={{ marginBottom: '1.5rem' }}>
        Summary Metrics
      </Typography.Title>
      
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4 mb-6">
        {/* Performance Metrics */}
        <MetricCard
          title="Average Response Time"
          value={`${avgResponseTime.toFixed(2)} ms`}
          description="Mean response time across all API requests"
        />
        
        <MetricCard
          title="Error Rate"
          value={`${(errorRate * 100).toFixed(2)}%`}
          description="Percentage of requests with 4xx/5xx status codes"
          valueColor={colors.error[500]}
        />
        
        <MetricCard
          title="Total Requests"
          value={totalRequests.toLocaleString()}
          description="Total number of API requests processed"
        />

        {/* Usage Metrics */}
        {usageData && (
          <>
            <MetricCard
              title="Active Users"
              value={activeUsers.toLocaleString()}
              description="Unique users with activity in selected time range"
            />
            
            <MetricCard
              title="Total Usage Events"
              value={totalEvents.toLocaleString()}
              description="Total user interaction events recorded"
            />
            
            <MetricCard
              title="Unique Users"
              value={uniqueUsers.toLocaleString()}
              description="Distinct users who triggered usage events"
            />
          </>
        )}

        {/* Percentile metrics if available */}
        {performanceData?.metrics?.p50_response_time_ms && (
          <>
            <MetricCard
              title="P50 Response Time"
              value={`${performanceData.metrics.p50_response_time_ms.toFixed(2)} ms`}
              description="50th percentile (median) response time"
            />
            
            <MetricCard
              title="P95 Response Time"
              value={`${performanceData.metrics.p95_response_time_ms.toFixed(2)} ms`}
              description="95th percentile response time"
            />
            
            <MetricCard
              title="P99 Response Time"
              value={`${performanceData.metrics.p99_response_time_ms.toFixed(2)} ms`}
              description="99th percentile response time"
            />
          </>
        )}
      </div>
      
      <div className="mt-4 text-xs text-gray-500">
        <p>
          <strong>Note:</strong> Active users count is calculated from both API requests (performance metrics) 
          and UI interactions (usage events) to avoid double-counting users who appear in both datasets.
        </p>
      </div>
    </div>
  );
};

