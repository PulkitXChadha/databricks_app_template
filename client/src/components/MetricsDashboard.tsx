import React, { useEffect, useState } from 'react';
import { MetricsService } from '../fastapi_client';
import { PerformanceChart } from './PerformanceChart';
import { EndpointBreakdownTable } from './EndpointBreakdownTable';
import { MetricsTable } from './MetricsTable';
import { UsageChart } from './UsageChart';
import { usageTracker } from '../services/usageTracker';

interface MetricsDashboardProps {
  className?: string;
}

export const MetricsDashboard: React.FC<MetricsDashboardProps> = ({ className }) => {
  const [timeRange, setTimeRange] = useState('24h');
  const [performanceData, setPerformanceData] = useState<any>(null);
  const [usageData, setUsageData] = useState<any>(null);
  const [timeSeriesData, setTimeSeriesData] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Load metrics on initial mount only (manual refresh pattern per FR-005)
  useEffect(() => {
    loadMetrics();
  }, []); // Empty dependency array - no auto-refresh on timeRange change

  const loadMetrics = async () => {
    setLoading(true);
    setError(null);
    
    try {
      const [perfData, usageDataResult, timeSeriesResult] = await Promise.all([
        MetricsService.getPerformanceMetricsApiV1MetricsPerformanceGet(timeRange),
        MetricsService.getUsageMetricsApiV1MetricsUsageGet(timeRange),
        MetricsService.getTimeSeriesMetricsApiV1MetricsTimeSeriesGet('both', timeRange)
      ]);
      
      setPerformanceData(perfData);
      setUsageData(usageDataResult);
      setTimeSeriesData(timeSeriesResult);
    } catch (err: any) {
      // FR-011: Admin access required
      if (err.status === 403) {
        setError('Admin access required. Only workspace administrators can view metrics.');
      } else if (err.status === 401) {
        setError('Authentication required. Please log in.');
      } else {
        setError(`Failed to load metrics: ${err.message || 'Unknown error'}`);
      }
      console.error('Failed to load metrics:', err);
    } finally {
      setLoading(false);
    }
  };

  // Manual refresh handler per FR-005
  const handleRefresh = () => {
    // Track refresh button click
    usageTracker.track({
      event_type: 'button_click',
      page_name: '/metrics',
      element_id: 'refresh-button',
      metadata: {
        time_range: timeRange,
        action: 'manual_refresh'
      }
    });
    
    loadMetrics();
  };

  // Error state
  if (error) {
    return (
      <div className={className}>
        <div className="bg-red-50 border border-red-200 text-red-800 px-4 py-3 rounded relative" role="alert">
          <span className="block sm:inline">{error}</span>
        </div>
        <button onClick={handleRefresh} className="mt-4 px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700">
          Retry
        </button>
      </div>
    );
  }

  // Loading state
  if (loading && !performanceData) {
    return <div className={className}>Loading metrics...</div>;
  }

  // Empty state per spec.md edge case
  const hasData = performanceData?.metrics || usageData?.metrics;
  if (!hasData) {
    return (
      <div className={className}>
        <div className="bg-blue-50 border border-blue-200 text-blue-800 px-4 py-3 rounded relative" role="alert">
          <span className="block sm:inline">
            No data available. Metrics will appear after application usage.
          </span>
        </div>
        <div className="mt-4">
          <button 
            onClick={handleRefresh} 
            disabled={loading} 
            data-testid="refresh-button"
            className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:bg-gray-400"
          >
            {loading ? 'Refreshing...' : 'Refresh'}
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className={className}>
      <div className="mb-6 flex justify-between items-center">
        <h1 className="text-3xl font-bold">Application Metrics</h1>
        <button 
          onClick={handleRefresh} 
          disabled={loading}
          data-testid="refresh-button"
          className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:bg-gray-400"
        >
          {loading ? 'Refreshing...' : 'Refresh'}
        </button>
      </div>

      {/* Time Range Selector - changing doesn't auto-refresh per clarification */}
      <div className="mb-6">
        <label htmlFor="time-range" className="block text-sm font-medium mb-2">
          Time Range
        </label>
        <select
          id="time-range"
          value={timeRange}
          onChange={(e) => {
            const newTimeRange = e.target.value;
            
            // Track time range change
            usageTracker.track({
              event_type: 'preference_changed',
              page_name: '/metrics',
              element_id: 'time-range-selector',
              metadata: {
                previous_time_range: timeRange,
                new_time_range: newTimeRange
              }
            });
            
            setTimeRange(newTimeRange);
          }}
          className="px-3 py-2 border rounded-md"
          data-track-id="time-range-selector"
        >
          <option value="24h">Last 24 Hours</option>
          <option value="7d">Last 7 Days</option>
          <option value="30d">Last 30 Days</option>
          <option value="90d">Last 90 Days</option>
        </select>
        <p className="text-sm text-gray-500 mt-1">
          Select a time range and click "Refresh" to update metrics.
        </p>
      </div>

      {/* Summary Metrics Table (T030.5) */}
      {(performanceData || usageData) && (
        <div className="mb-8">
          <MetricsTable performanceData={performanceData} usageData={usageData} />
        </div>
      )}

      {/* Performance Chart (T029, T102) - now uses time-series data */}
      {timeSeriesData && (
        <div className="mb-8">
          <PerformanceChart data={timeSeriesData} timeRange={timeRange} />
        </div>
      )}

      {/* Endpoint Breakdown Table (T030) */}
      {performanceData?.endpoints && performanceData.endpoints.length > 0 && (
        <div className="mb-8">
          <EndpointBreakdownTable endpoints={performanceData.endpoints} />
        </div>
      )}

      {/* T086-T088, T103: Usage Chart with event distribution and page views - now uses time-series data */}
      {usageData && timeSeriesData && (
        <div className="mb-8">
          <UsageChart summaryData={usageData} timeSeriesData={timeSeriesData} timeRange={timeRange} />
        </div>
      )}
    </div>
  );
};

