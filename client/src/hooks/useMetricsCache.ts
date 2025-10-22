import { useState, useEffect, useCallback, useRef } from 'react';
import { MetricsService } from '../fastapi_client';

interface MetricsData {
  performanceData: any;
  usageData: any;
  timeSeriesData: any;
}

interface MetricsCacheState {
  data: MetricsData | null;
  loading: boolean;
  error: string | null;
  lastFetch: number | null;
}

// Global cache shared across all instances - keyed by time range
const globalCache = new Map<string, MetricsCacheState>();

// Subscribers to notify when cache updates - keyed by time range
const subscribers = new Map<string, Set<() => void>>();

// Refresh interval in milliseconds (5 minutes)
const REFRESH_INTERVAL = 5 * 60 * 1000;

// Background refresh timers - one per time range
const refreshTimers = new Map<string, NodeJS.Timeout>();

// Get or create cache entry for a time range
const getCacheEntry = (timeRange: string): MetricsCacheState => {
  if (!globalCache.has(timeRange)) {
    globalCache.set(timeRange, {
      data: null,
      loading: false,
      error: null,
      lastFetch: null,
    });
  }
  return globalCache.get(timeRange)!;
};

// Get or create subscriber set for a time range
const getSubscribers = (timeRange: string): Set<() => void> => {
  if (!subscribers.has(timeRange)) {
    subscribers.set(timeRange, new Set());
  }
  return subscribers.get(timeRange)!;
};

/**
 * Custom hook to manage metrics data with caching and background refresh
 * - Loads data only once per time range on first use
 * - Refreshes automatically every 5 minutes in the background
 * - Shares state across all instances of the hook
 * - Caches data separately for each time range
 */
export const useMetricsCache = (timeRange: string) => {
  const [state, setState] = useState<MetricsCacheState>(() => getCacheEntry(timeRange));
  const isMountedRef = useRef(true);
  const currentTimeRangeRef = useRef(timeRange);

  // Subscribe to cache updates for the current time range
  useEffect(() => {
    isMountedRef.current = true;
    currentTimeRangeRef.current = timeRange;

    const updateState = () => {
      if (isMountedRef.current) {
        setState({ ...getCacheEntry(timeRange) });
      }
    };

    const subs = getSubscribers(timeRange);
    subs.add(updateState);

    // Update state immediately when time range changes
    updateState();

    return () => {
      isMountedRef.current = false;
      subs.delete(updateState);
    };
  }, [timeRange]);

  // Notify all subscribers of cache update for a specific time range
  const notifySubscribers = useCallback((tr: string) => {
    const subs = getSubscribers(tr);
    subs.forEach(callback => callback());
  }, []);

  // Load metrics from API for a specific time range
  const loadMetrics = useCallback(async (tr: string, showLoading = true) => {
    const cache = getCacheEntry(tr);
    
    // Don't start a new fetch if one is already in progress for this time range
    if (cache.loading) {
      return;
    }

    if (showLoading) {
      cache.loading = true;
      cache.error = null;
      notifySubscribers(tr);
    }

    try {
      const [perfData, usageDataResult, timeSeriesResult] = await Promise.all([
        MetricsService.getPerformanceMetricsApiV1MetricsPerformanceGet(tr),
        MetricsService.getUsageMetricsApiV1MetricsUsageGet(tr),
        MetricsService.getTimeSeriesMetricsApiV1MetricsTimeSeriesGet('both', tr)
      ]);

      cache.data = {
        performanceData: perfData,
        usageData: usageDataResult,
        timeSeriesData: timeSeriesResult,
      };
      cache.error = null;
      cache.lastFetch = Date.now();
    } catch (err: any) {
      // FR-011: Admin access required
      if (err.status === 403) {
        cache.error = 'Admin access required. Only workspace administrators can view metrics.';
      } else if (err.status === 401) {
        cache.error = 'Authentication required. Please log in.';
      } else {
        cache.error = `Failed to load metrics: ${err.message || 'Unknown error'}`;
      }
      console.error('Failed to load metrics:', err);
    } finally {
      cache.loading = false;
      notifySubscribers(tr);
    }
  }, [notifySubscribers]);

  // Start background refresh timer for a specific time range
  const startBackgroundRefresh = useCallback((tr: string) => {
    // Clear existing timer for this time range
    const existingTimer = refreshTimers.get(tr);
    if (existingTimer) {
      clearInterval(existingTimer);
    }

    // Set up new timer
    const timer = setInterval(() => {
      console.log(`Background refresh: Loading metrics for ${tr}...`);
      // Background refresh should not show loading spinner
      loadMetrics(tr, false);
    }, REFRESH_INTERVAL);
    
    refreshTimers.set(tr, timer);
  }, [loadMetrics]);

  // Stop background refresh timer for a specific time range
  const stopBackgroundRefresh = useCallback((tr: string) => {
    const timer = refreshTimers.get(tr);
    if (timer) {
      clearInterval(timer);
      refreshTimers.delete(tr);
    }
  }, []);

  // Initialize: Load data if not already loaded for this time range
  useEffect(() => {
    const cache = getCacheEntry(timeRange);
    const shouldLoad = !cache.data && !cache.loading;
    
    if (shouldLoad) {
      // If data is not cached, show loading spinner
      loadMetrics(timeRange, true);
    } else if (cache.data) {
      // If data is cached, refresh in background without loading spinner
      loadMetrics(timeRange, false);
    }

    // Start background refresh for this time range
    startBackgroundRefresh(timeRange);

    // Cleanup on unmount of last subscriber for this time range
    return () => {
      const subs = getSubscribers(timeRange);
      // Only stop refresh if there are no more subscribers for this time range
      if (subs.size === 0) {
        stopBackgroundRefresh(timeRange);
      }
    };
  }, [timeRange, loadMetrics, startBackgroundRefresh, stopBackgroundRefresh]);

  // Manual refresh function
  const refresh = useCallback(() => {
    loadMetrics(timeRange, true);
  }, [timeRange, loadMetrics]);

  return {
    performanceData: state.data?.performanceData ?? null,
    usageData: state.data?.usageData ?? null,
    timeSeriesData: state.data?.timeSeriesData ?? null,
    loading: state.loading,
    error: state.error,
    refresh,
  };
};

