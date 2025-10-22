/**
 * UsageChart Component
 * 
 * T085: Displays usage metrics visualization using Recharts.
 * T103: Updated to use time-series data for trends over time.
 */

import React from 'react';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts';
import { Card, Typography, colors } from 'designbricks';

interface UsageChartProps {
  summaryData: any; // Contains event_distribution and page_views
  timeSeriesData: any; // Contains time-series data points
  timeRange: string;
}

export const UsageChart: React.FC<UsageChartProps> = ({ summaryData, timeSeriesData, timeRange }) => {
  if (!summaryData || !summaryData.event_distribution) {
    return (
      <div className="bg-white p-6 rounded-lg shadow">
        <h2 className="text-xl font-semibold mb-4">Usage Events</h2>
        <p className="text-gray-500">No usage data available</p>
      </div>
    );
  }

  // Determine interval from data or default based on time range
  const interval = timeSeriesData?.interval || (timeRange === '24h' ? '5min' : 'hourly');
  const is5MinInterval = interval === '5min';

  // Transform time-series data for Recharts
  const timeSeriesChartData = (timeSeriesData?.data_points || []).map((point: any) => {
    const date = new Date(point.timestamp);
    let formattedTime;
    
    // Format timestamp based on interval
    if (is5MinInterval) {
      // For 5-minute intervals, show time only
      formattedTime = date.toLocaleTimeString('en-US', {
        hour: '2-digit',
        minute: '2-digit',
      });
    } else {
      // For hourly intervals, show date and time
      formattedTime = date.toLocaleTimeString('en-US', {
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
      });
    }
    
    return {
      timestamp: formattedTime,
      totalEvents: point.total_events || 0,
      uniqueUsers: point.unique_users || 0,
    };
  });

  // Colors for different event types
  const eventColors: Record<string, string> = {
    page_view: '#3b82f6', // blue
    button_click: '#10b981', // green
    form_submit: '#f59e0b', // amber
    query_executed: '#8b5cf6', // purple
    model_invoked: '#ec4899', // pink
    preference_changed: '#14b8a6', // teal
    data_source_selected: '#f97316', // orange
    schema_detected: '#6366f1', // indigo
    file_uploaded: '#06b6d4', // cyan
    export_triggered: '#84cc16', // lime
  };

  return (
    <div className="bg-white p-6 rounded-lg shadow">
      <h2 className="text-xl font-semibold mb-4">Usage Events Distribution</h2>
      <p className="text-sm text-gray-600 mb-4">
        Event breakdown for {timeRange}
      </p>

      {/* Summary Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
        <Card padding="medium" className="h-full">
          <div className="flex flex-col space-y-2">
            <Typography.Text color="secondary" style={{ fontSize: '0.875rem', textTransform: 'uppercase', fontWeight: 500 }}>
              Total Events
            </Typography.Text>
            <Typography.Title 
              level={2} 
              withoutMargins 
              style={{ color: colors.info[500] }}
            >
              {(summaryData.metrics?.total_events || 0).toLocaleString()}
            </Typography.Title>
            <Typography.Text color="secondary" style={{ fontSize: '0.875rem' }}>
              Total user interaction events recorded
            </Typography.Text>
          </div>
        </Card>
        
        <Card padding="medium" className="h-full">
          <div className="flex flex-col space-y-2">
            <Typography.Text color="secondary" style={{ fontSize: '0.875rem', textTransform: 'uppercase', fontWeight: 500 }}>
              Unique Users
            </Typography.Text>
            <Typography.Title 
              level={2} 
              withoutMargins 
              style={{ color: colors.success[500] }}
            >
              {(summaryData.metrics?.unique_users || 0).toLocaleString()}
            </Typography.Title>
            <Typography.Text color="secondary" style={{ fontSize: '0.875rem' }}>
              Distinct users who triggered usage events
            </Typography.Text>
          </div>
        </Card>
        
        <Card padding="medium" className="h-full">
          <div className="flex flex-col space-y-2">
            <Typography.Text color="secondary" style={{ fontSize: '0.875rem', textTransform: 'uppercase', fontWeight: 500 }}>
              Event Types
            </Typography.Text>
            <Typography.Title 
              level={2} 
              withoutMargins
            >
              {Object.keys(summaryData.event_distribution || {}).length}
            </Typography.Title>
            <Typography.Text color="secondary" style={{ fontSize: '0.875rem' }}>
              Different types of events tracked
            </Typography.Text>
          </div>
        </Card>
      </div>

      {/* Time-Series Chart for Usage Trends */}
      {timeSeriesChartData.length > 0 && (
        <div className="mb-6">
          <h3 className="text-lg font-semibold mb-3">Usage Trend Over Time</h3>
          <ResponsiveContainer width="100%" height={300}>
            <LineChart data={timeSeriesChartData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis 
                dataKey="timestamp" 
                tick={{ fontSize: 12 }}
                angle={-45}
                textAnchor="end"
                height={80}
                interval={is5MinInterval ? 'preserveStartEnd' : 'preserveStart'}
              />
              <YAxis 
                yAxisId="left"
                label={{ value: 'Total Events', angle: -90, position: 'insideLeft' }}
                tick={{ fontSize: 12 }}
              />
              <YAxis 
                yAxisId="right"
                orientation="right"
                label={{ value: 'Unique Users', angle: 90, position: 'insideRight' }}
                tick={{ fontSize: 12 }}
              />
              <Tooltip contentStyle={{ fontSize: 12 }} />
              <Legend wrapperStyle={{ fontSize: 12 }} />
              <Line 
                yAxisId="left"
                type="monotone" 
                dataKey="totalEvents" 
                stroke="#3b82f6" 
                strokeWidth={2}
                name="Total Events"
                dot={false}
              />
              <Line 
                yAxisId="right"
                type="monotone" 
                dataKey="uniqueUsers" 
                stroke="#10b981" 
                strokeWidth={2}
                name="Unique Users"
                dot={false}
                strokeDasharray="5 5"
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* Page Views Breakdown (if available) */}
      {summaryData.page_views && Object.keys(summaryData.page_views).length > 0 && (
        <div className="mt-6">
          <h3 className="text-lg font-semibold mb-3">Top Pages by Views</h3>
          <div className="space-y-2">
            {Object.entries(summaryData.page_views)
              .sort(([, a], [, b]) => (b as number) - (a as number))
              .slice(0, 5)
              .map(([page, views]) => (
                <div key={page} className="flex justify-between items-center p-2 bg-gray-50 rounded">
                  <span className="text-sm font-medium">{page}</span>
                  <span className="text-sm text-gray-600">{(views as number).toLocaleString()} views</span>
                </div>
              ))}
          </div>
        </div>
      )}
    </div>
  );
};

