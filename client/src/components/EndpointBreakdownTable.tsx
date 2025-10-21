import React, { useState, useMemo } from 'react';

interface EndpointMetric {
  endpoint: string;
  method: string;
  avg_response_time_ms: number;
  p50_response_time_ms?: number;
  p95_response_time_ms?: number;
  p99_response_time_ms?: number;
  request_count: number;
  error_count: number;
  error_rate?: number;
}

interface EndpointBreakdownTableProps {
  endpoints: EndpointMetric[];
}

type SortColumn = keyof EndpointMetric;
type SortDirection = 'asc' | 'desc';

export const EndpointBreakdownTable: React.FC<EndpointBreakdownTableProps> = ({ endpoints }) => {
  const [sortColumn, setSortColumn] = useState<SortColumn>('avg_response_time_ms');
  const [sortDirection, setSortDirection] = useState<SortDirection>('desc');

  // Sort endpoints by selected column
  const sortedEndpoints = useMemo(() => {
    if (!endpoints || endpoints.length === 0) return [];
    
    return [...endpoints].sort((a, b) => {
      const aVal = a[sortColumn];
      const bVal = b[sortColumn];
      
      // Handle undefined values
      if (aVal === undefined && bVal === undefined) return 0;
      if (aVal === undefined) return sortDirection === 'asc' ? 1 : -1;
      if (bVal === undefined) return sortDirection === 'asc' ? -1 : 1;
      
      const multiplier = sortDirection === 'asc' ? 1 : -1;
      
      // String comparison for text fields
      if (typeof aVal === 'string' && typeof bVal === 'string') {
        return aVal.localeCompare(bVal) * multiplier;
      }
      
      // Numeric comparison
      return (aVal < bVal ? -1 : aVal > bVal ? 1 : 0) * multiplier;
    });
  }, [endpoints, sortColumn, sortDirection]);

  const handleSort = (column: SortColumn) => {
    if (sortColumn === column) {
      setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc');
    } else {
      setSortColumn(column);
      setSortDirection('desc');
    }
  };

  const getSortIcon = (column: SortColumn) => {
    if (sortColumn !== column) return '↕️';
    return sortDirection === 'asc' ? '↑' : '↓';
  };

  if (!endpoints || endpoints.length === 0) {
    return (
      <div className="bg-white p-6 rounded-lg shadow">
        <h2 className="text-xl font-bold mb-4">Endpoint Performance Breakdown</h2>
        <p className="text-gray-500 text-sm">No endpoint data available</p>
      </div>
    );
  }

  return (
    <div className="bg-white p-6 rounded-lg shadow">
      <h2 className="text-xl font-bold mb-4">Endpoint Performance Breakdown</h2>
      <p className="text-sm text-gray-600 mb-4">
        All tracked API endpoints sorted by average response time (click column headers to sort)
      </p>
      
      <div className="overflow-x-auto">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th
                onClick={() => handleSort('endpoint')}
                className="px-4 py-3 text-left text-xs font-medium text-gray-700 uppercase tracking-wider cursor-pointer hover:bg-gray-100"
              >
                Endpoint {getSortIcon('endpoint')}
              </th>
              <th
                onClick={() => handleSort('method')}
                className="px-4 py-3 text-left text-xs font-medium text-gray-700 uppercase tracking-wider cursor-pointer hover:bg-gray-100"
              >
                Method {getSortIcon('method')}
              </th>
              <th
                onClick={() => handleSort('avg_response_time_ms')}
                className="px-4 py-3 text-left text-xs font-medium text-gray-700 uppercase tracking-wider cursor-pointer hover:bg-gray-100"
              >
                Avg Response (ms) {getSortIcon('avg_response_time_ms')}
              </th>
              {endpoints.some(e => e.p50_response_time_ms !== undefined) && (
                <>
                  <th
                    onClick={() => handleSort('p50_response_time_ms')}
                    className="px-4 py-3 text-left text-xs font-medium text-gray-700 uppercase tracking-wider cursor-pointer hover:bg-gray-100"
                  >
                    P50 (ms) {getSortIcon('p50_response_time_ms')}
                  </th>
                  <th
                    onClick={() => handleSort('p95_response_time_ms')}
                    className="px-4 py-3 text-left text-xs font-medium text-gray-700 uppercase tracking-wider cursor-pointer hover:bg-gray-100"
                  >
                    P95 (ms) {getSortIcon('p95_response_time_ms')}
                  </th>
                  <th
                    onClick={() => handleSort('p99_response_time_ms')}
                    className="px-4 py-3 text-left text-xs font-medium text-gray-700 uppercase tracking-wider cursor-pointer hover:bg-gray-100"
                  >
                    P99 (ms) {getSortIcon('p99_response_time_ms')}
                  </th>
                </>
              )}
              <th
                onClick={() => handleSort('request_count')}
                className="px-4 py-3 text-left text-xs font-medium text-gray-700 uppercase tracking-wider cursor-pointer hover:bg-gray-100"
              >
                Requests {getSortIcon('request_count')}
              </th>
              <th
                onClick={() => handleSort('error_rate')}
                className="px-4 py-3 text-left text-xs font-medium text-gray-700 uppercase tracking-wider cursor-pointer hover:bg-gray-100"
              >
                Error Rate {getSortIcon('error_rate')}
              </th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {sortedEndpoints.map((endpoint, idx) => (
              <tr key={idx} className="hover:bg-gray-50">
                <td className="px-4 py-3 whitespace-nowrap text-sm font-mono text-gray-900">
                  {endpoint.endpoint}
                </td>
                <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-600">
                  <span className="px-2 py-1 text-xs font-semibold rounded bg-blue-100 text-blue-800">
                    {endpoint.method}
                  </span>
                </td>
                <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-900">
                  {endpoint.avg_response_time_ms.toFixed(2)}
                </td>
                {endpoints.some(e => e.p50_response_time_ms !== undefined) && (
                  <>
                    <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-600">
                      {endpoint.p50_response_time_ms?.toFixed(2) || 'N/A'}
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-600">
                      {endpoint.p95_response_time_ms?.toFixed(2) || 'N/A'}
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-600">
                      {endpoint.p99_response_time_ms?.toFixed(2) || 'N/A'}
                    </td>
                  </>
                )}
                <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-600">
                  {endpoint.request_count.toLocaleString()}
                </td>
                <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-600">
                  {endpoint.error_rate !== undefined
                    ? `${(endpoint.error_rate * 100).toFixed(2)}%`
                    : endpoint.error_count > 0
                    ? `${endpoint.error_count} errors`
                    : '0%'}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      
      <div className="mt-4 text-xs text-gray-500">
        <p>
          <strong>Total endpoints:</strong> {sortedEndpoints.length} |{' '}
          <strong>Default sort:</strong> Average response time (slowest first) |{' '}
          <strong>P50/P95/P99:</strong> 50th, 95th, and 99th percentile response times
        </p>
      </div>
    </div>
  );
};

