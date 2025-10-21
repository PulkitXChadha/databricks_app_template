import React from 'react';

interface MetricsTableProps {
  performanceData: any;
  usageData: any;
}

export const MetricsTable: React.FC<MetricsTableProps> = ({ performanceData, usageData }) => {
  // Calculate active users from both performance and usage data
  const activeUsers = usageData?.metrics?.active_users || 0;
  const totalRequests = performanceData?.metrics?.total_requests || 0;
  const avgResponseTime = performanceData?.metrics?.avg_response_time_ms || 0;
  const errorRate = performanceData?.metrics?.error_rate || 0;
  const totalEvents = usageData?.metrics?.total_events || 0;
  const uniqueUsers = usageData?.metrics?.unique_users || 0;

  return (
    <div className="bg-white p-6 rounded-lg shadow">
      <h2 className="text-xl font-bold mb-4">Summary Metrics</h2>
      
      <div className="overflow-x-auto">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-700 uppercase tracking-wider">
                Metric
              </th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-700 uppercase tracking-wider">
                Value
              </th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-700 uppercase tracking-wider">
                Description
              </th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {/* Performance Metrics */}
            <tr className="hover:bg-gray-50">
              <td className="px-4 py-3 whitespace-nowrap text-sm font-medium text-gray-900">
                Average Response Time
              </td>
              <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-600">
                <span className="font-bold text-lg">{avgResponseTime.toFixed(2)} ms</span>
              </td>
              <td className="px-4 py-3 text-sm text-gray-500">
                Mean response time across all API requests
              </td>
            </tr>
            
            <tr className="hover:bg-gray-50">
              <td className="px-4 py-3 whitespace-nowrap text-sm font-medium text-gray-900">
                Error Rate
              </td>
              <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-600">
                <span className={`font-bold text-lg ${errorRate > 0.05 ? 'text-red-600' : 'text-green-600'}`}>
                  {(errorRate * 100).toFixed(2)}%
                </span>
              </td>
              <td className="px-4 py-3 text-sm text-gray-500">
                Percentage of requests with 4xx/5xx status codes
              </td>
            </tr>
            
            <tr className="hover:bg-gray-50">
              <td className="px-4 py-3 whitespace-nowrap text-sm font-medium text-gray-900">
                Total Requests
              </td>
              <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-600">
                <span className="font-bold text-lg">{totalRequests.toLocaleString()}</span>
              </td>
              <td className="px-4 py-3 text-sm text-gray-500">
                Total number of API requests processed
              </td>
            </tr>

            {/* Usage Metrics */}
            {usageData && (
              <>
                <tr className="bg-blue-50 hover:bg-blue-100">
                  <td className="px-4 py-3 whitespace-nowrap text-sm font-medium text-gray-900">
                    Active Users
                  </td>
                  <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-600">
                    <span className="font-bold text-lg">{activeUsers.toLocaleString()}</span>
                  </td>
                  <td className="px-4 py-3 text-sm text-gray-500">
                    Unique users with activity in selected time range
                  </td>
                </tr>
                
                <tr className="hover:bg-gray-50">
                  <td className="px-4 py-3 whitespace-nowrap text-sm font-medium text-gray-900">
                    Total Usage Events
                  </td>
                  <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-600">
                    <span className="font-bold text-lg">{totalEvents.toLocaleString()}</span>
                  </td>
                  <td className="px-4 py-3 text-sm text-gray-500">
                    Total user interaction events recorded
                  </td>
                </tr>
                
                <tr className="hover:bg-gray-50">
                  <td className="px-4 py-3 whitespace-nowrap text-sm font-medium text-gray-900">
                    Unique Users
                  </td>
                  <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-600">
                    <span className="font-bold text-lg">{uniqueUsers.toLocaleString()}</span>
                  </td>
                  <td className="px-4 py-3 text-sm text-gray-500">
                    Distinct users who triggered usage events
                  </td>
                </tr>
              </>
            )}

            {/* Percentile metrics if available */}
            {performanceData?.metrics?.p50_response_time_ms && (
              <>
                <tr className="hover:bg-gray-50">
                  <td className="px-4 py-3 whitespace-nowrap text-sm font-medium text-gray-900">
                    P50 Response Time
                  </td>
                  <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-600">
                    <span className="font-bold text-lg">
                      {performanceData.metrics.p50_response_time_ms.toFixed(2)} ms
                    </span>
                  </td>
                  <td className="px-4 py-3 text-sm text-gray-500">
                    50th percentile (median) response time
                  </td>
                </tr>
                
                <tr className="hover:bg-gray-50">
                  <td className="px-4 py-3 whitespace-nowrap text-sm font-medium text-gray-900">
                    P95 Response Time
                  </td>
                  <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-600">
                    <span className="font-bold text-lg">
                      {performanceData.metrics.p95_response_time_ms.toFixed(2)} ms
                    </span>
                  </td>
                  <td className="px-4 py-3 text-sm text-gray-500">
                    95th percentile response time
                  </td>
                </tr>
                
                <tr className="hover:bg-gray-50">
                  <td className="px-4 py-3 whitespace-nowrap text-sm font-medium text-gray-900">
                    P99 Response Time
                  </td>
                  <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-600">
                    <span className="font-bold text-lg">
                      {performanceData.metrics.p99_response_time_ms.toFixed(2)} ms
                    </span>
                  </td>
                  <td className="px-4 py-3 text-sm text-gray-500">
                    99th percentile response time
                  </td>
                </tr>
              </>
            )}
          </tbody>
        </table>
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

