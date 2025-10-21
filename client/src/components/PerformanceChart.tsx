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

interface PerformanceChartProps {
  data: any;
  timeRange: string;
}

export const PerformanceChart: React.FC<PerformanceChartProps> = ({ data, timeRange }) => {
  // T102: Updated to use time-series API data_points
  if (!data?.data_points || data.data_points.length === 0) {
    return (
      <div className="bg-white p-6 rounded-lg shadow">
        <h2 className="text-xl font-bold mb-4">Response Time Trend</h2>
        <p className="text-gray-500 text-sm">
          No time-series data available for the selected range.
        </p>
      </div>
    );
  }

  // Transform data for Recharts format
  const chartData = data.data_points.map((point: any) => ({
    timestamp: new Date(point.timestamp).toLocaleTimeString('en-US', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    }),
    avgResponseTime: point.avg_response_time_ms || 0,
    errorRate: point.error_rate ? point.error_rate * 100 : 0, // Convert to percentage for display
  }));

  return (
    <div className="bg-white p-6 rounded-lg shadow">
      <h2 className="text-xl font-bold mb-4">Response Time Trend ({timeRange})</h2>
      <ResponsiveContainer width="100%" height={300}>
        <LineChart data={chartData}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis 
            dataKey="timestamp" 
            tick={{ fontSize: 12 }}
            angle={-45}
            textAnchor="end"
            height={80}
          />
          <YAxis 
            yAxisId="left"
            label={{ value: 'Response Time (ms)', angle: -90, position: 'insideLeft' }}
            tick={{ fontSize: 12 }}
          />
          <YAxis 
            yAxisId="right"
            orientation="right"
            label={{ value: 'Error Rate (%)', angle: 90, position: 'insideRight' }}
            tick={{ fontSize: 12 }}
          />
          <Tooltip 
            contentStyle={{ fontSize: 12 }}
            formatter={(value: number, name: string) => {
              if (name === 'Average Response Time') {
                return `${value.toFixed(2)} ms`;
              }
              return `${value.toFixed(2)}%`;
            }}
          />
          <Legend wrapperStyle={{ fontSize: 12 }} />
          <Line
            yAxisId="left"
            type="monotone"
            dataKey="avgResponseTime"
            stroke="#0066CC"
            strokeWidth={2}
            name="Average Response Time"
            dot={false}
          />
          <Line
            yAxisId="right"
            type="monotone"
            dataKey="errorRate"
            stroke="#FF6B6B"
            strokeWidth={2}
            name="Error Rate"
            dot={false}
            strokeDasharray="5 5"
          />
        </LineChart>
      </ResponsiveContainer>
      <p className="text-xs text-gray-500 mt-2">
        Response time and error rate trends over time. Data aggregated hourly.
      </p>
    </div>
  );
};

