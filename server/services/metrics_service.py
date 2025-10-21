"""Metrics service for collecting, storing, and querying application metrics.

This service handles performance metrics (API requests) and usage events
(user interactions), routing queries to raw vs aggregated tables based on
time range.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from sqlalchemy import Integer, and_, func
from sqlalchemy.orm import Session

from server.models.aggregated_metric import AggregatedMetric
from server.models.performance_metric import PerformanceMetric
from server.models.usage_event import UsageEvent

logger = logging.getLogger(__name__)


class MetricsService:
    """Service for metrics collection and retrieval.

    Automatically routes queries to:
    - Raw tables (performance_metrics, usage_events) for last 7 days
    - Aggregated table (aggregated_metrics) for 8-90 days ago
    """

    def __init__(self, db: Session):
        """Initialize metrics service.

        Args:
            db: SQLAlchemy database session
        """
        self.db = db

    def get_performance_metrics(
        self,
        time_range: str = '24h',
        endpoint: Optional[str] = None
    ) -> Dict:
        """Retrieve aggregated performance metrics.

        Args:
            time_range: Time range ("24h", "7d", "30d", "90d")
            endpoint: Optional endpoint filter

        Returns:
            Dictionary with aggregated performance metrics
        """
        start_time, end_time = self._parse_time_range(time_range)

        # Route query based on time range
        if (datetime.utcnow() - start_time).days <= 7:
            return self._query_raw_performance_metrics(start_time, end_time, endpoint)
        else:
            return self._query_aggregated_performance_metrics(start_time, end_time, endpoint)

    def get_usage_metrics(
        self,
        time_range: str = '24h',
        event_type: Optional[str] = None
    ) -> Dict:
        """Retrieve aggregated usage metrics.

        Args:
            time_range: Time range ("24h", "7d", "30d", "90d")
            event_type: Optional event type filter

        Returns:
            Dictionary with aggregated usage metrics
        """
        start_time, end_time = self._parse_time_range(time_range)

        if (datetime.utcnow() - start_time).days <= 7:
            return self._query_raw_usage_metrics(start_time, end_time, event_type)
        else:
            return self._query_aggregated_usage_metrics(start_time, end_time, event_type)

    def record_performance_metric(self, metric_data: Dict) -> None:
        """Record a single performance metric (async write).

        Args:
            metric_data: Dictionary with metric fields
        """
        try:
            metric = PerformanceMetric(**metric_data)
            self.db.add(metric)
            self.db.commit()
            logger.debug(
                f'Recorded performance metric: {metric.endpoint} - '
                f'{metric.response_time_ms}ms (status: {metric.status_code})'
            )
        except Exception as e:
            # Suppress verbose logging for database connection errors
            if 'Database instance is not found' in str(e):
                logger.debug('Skipping performance metric - database unavailable')
            else:
                logger.error(f'Failed to record performance metric: {e}')
            self.db.rollback()
            # Don't raise - graceful degradation per FR-007

    def record_usage_events_batch(self, events: List[Dict], user_id: str) -> int:
        """Record batch of usage events.

        Args:
            events: List of event dictionaries
            user_id: User ID for all events

        Returns:
            Number of events successfully recorded
        """
        try:
            event_objects = [
                UsageEvent(**{**event, 'user_id': user_id})
                for event in events
            ]
            self.db.bulk_save_objects(event_objects)
            self.db.commit()
            logger.info(f'Recorded {len(event_objects)} usage events for user {user_id}')
            return len(event_objects)
        except Exception as e:
            logger.error(f'Failed to record usage events batch: {e}', exc_info=True)
            self.db.rollback()
            return 0

    def _parse_time_range(self, time_range: str) -> tuple[datetime, datetime]:
        """Parse time range string to start/end datetimes.

        Args:
            time_range: Time range string ("24h", "7d", "30d", "90d")

        Returns:
            Tuple of (start_time, end_time)
        """
        end_time = datetime.utcnow()

        if time_range == '24h':
            start_time = end_time - timedelta(hours=24)
        elif time_range == '7d':
            start_time = end_time - timedelta(days=7)
        elif time_range == '30d':
            start_time = end_time - timedelta(days=30)
        elif time_range == '90d':
            start_time = end_time - timedelta(days=90)
        else:
            # Default to 24 hours
            start_time = end_time - timedelta(hours=24)

        return start_time, end_time

    def _query_raw_performance_metrics(
        self,
        start_time: datetime,
        end_time: datetime,
        endpoint: Optional[str]
    ) -> Dict:
        """Query raw performance metrics table (<7 days old).

        Args:
            start_time: Start of time range
            end_time: End of time range
            endpoint: Optional endpoint filter

        Returns:
            Dictionary with aggregated metrics
        """
        try:
            query = self.db.query(PerformanceMetric).filter(
                and_(
                    PerformanceMetric.timestamp >= start_time,
                    PerformanceMetric.timestamp <= end_time
                )
            )

            if endpoint:
                query = query.filter(PerformanceMetric.endpoint == endpoint)

            metrics = query.all()

            if not metrics:
                return self._empty_performance_response(start_time, end_time)
        except Exception as e:
            # Handle database connection errors gracefully
            logger.warning(f'Failed to query performance metrics: {e}')
            return self._empty_performance_response(start_time, end_time)

        # Aggregate in Python
        response_times = [m.response_time_ms for m in metrics]
        total_requests = len(metrics)
        error_count = sum(1 for m in metrics if m.status_code >= 400)

        return {
            'time_range': self._format_time_range(start_time, end_time),
            'start_time': start_time.isoformat(),
            'end_time': end_time.isoformat(),
            'metrics': {
                'avg_response_time_ms': sum(response_times) / len(response_times),
                'total_requests': total_requests,
                'error_rate': error_count / total_requests if total_requests > 0 else 0.0,
                'p50_response_time_ms': self._percentile(response_times, 0.5),
                'p95_response_time_ms': self._percentile(response_times, 0.95),
                'p99_response_time_ms': self._percentile(response_times, 0.99),
            },
            'endpoints': self._aggregate_by_endpoint(metrics)
        }

    def _query_aggregated_performance_metrics(
        self,
        start_time: datetime,
        end_time: datetime,
        endpoint: Optional[str]
    ) -> Dict:
        """Query aggregated metrics table (8-90 days old).

        Args:
            start_time: Start of time range
            end_time: End of time range
            endpoint: Optional endpoint filter

        Returns:
            Dictionary with aggregated metrics
        """
        # TODO: Implement aggregated query in User Story 4
        return self._empty_performance_response(start_time, end_time)

    def _query_raw_usage_metrics(
        self,
        start_time: datetime,
        end_time: datetime,
        event_type: Optional[str]
    ) -> Dict:
        """Query raw usage events table (<7 days old).

        Args:
            start_time: Start of time range
            end_time: End of time range
            event_type: Optional event type filter

        Returns:
            Dictionary with aggregated usage metrics
        """
        # TODO: Implement in User Story 3
        return {}

    def _query_aggregated_usage_metrics(
        self,
        start_time: datetime,
        end_time: datetime,
        event_type: Optional[str]
    ) -> Dict:
        """Query aggregated usage metrics table (8-90 days old).

        Args:
            start_time: Start of time range
            end_time: End of time range
            event_type: Optional event type filter

        Returns:
            Dictionary with aggregated usage metrics
        """
        # TODO: Implement in User Story 4
        return {}

    def _percentile(self, data: List[float], p: float) -> float:
        """Calculate percentile of data.

        Args:
            data: List of numeric values
            p: Percentile (0.0 to 1.0)

        Returns:
            Percentile value
        """
        if not data:
            return 0.0
        sorted_data = sorted(data)
        index = int(len(sorted_data) * p)
        return sorted_data[min(index, len(sorted_data) - 1)]

    def _aggregate_by_endpoint(self, metrics: List[PerformanceMetric]) -> List[Dict]:
        """Aggregate metrics by endpoint and method.

        Args:
            metrics: List of PerformanceMetric objects

        Returns:
            List of per-endpoint statistics sorted by avg_response_time_ms descending
        """
        endpoint_groups = {}
        for m in metrics:
            key = (m.endpoint, m.method)
            if key not in endpoint_groups:
                endpoint_groups[key] = []
            endpoint_groups[key].append(m)

        endpoint_stats = []
        for (endpoint, method), group in endpoint_groups.items():
            response_times = [m.response_time_ms for m in group]
            error_count = sum(1 for m in group if m.status_code >= 400)
            request_count = len(group)

            endpoint_stats.append({
                'endpoint': endpoint,
                'method': method,
                'avg_response_time_ms': sum(response_times) / len(response_times),
                'p50_response_time_ms': self._percentile(response_times, 0.5),
                'p95_response_time_ms': self._percentile(response_times, 0.95),
                'p99_response_time_ms': self._percentile(response_times, 0.99),
                'request_count': request_count,
                'error_count': error_count,
                'error_rate': error_count / request_count if request_count > 0 else 0.0,
            })

        # Sort by avg_response_time_ms descending (slowest first) per SC-005
        endpoint_stats.sort(key=lambda x: x['avg_response_time_ms'], reverse=True)

        return endpoint_stats

    def _empty_performance_response(
        self,
        start_time: datetime,
        end_time: datetime
    ) -> Dict:
        """Generate empty performance response structure.

        Args:
            start_time: Start of time range
            end_time: End of time range

        Returns:
            Empty response dictionary
        """
        return {
            'time_range': self._format_time_range(start_time, end_time),
            'start_time': start_time.isoformat(),
            'end_time': end_time.isoformat(),
            'metrics': {
                'avg_response_time_ms': 0.0,
                'total_requests': 0,
                'error_rate': 0.0,
                'p50_response_time_ms': 0.0,
                'p95_response_time_ms': 0.0,
                'p99_response_time_ms': 0.0,
            },
            'endpoints': []
        }

    def _format_time_range(self, start_time: datetime, end_time: datetime) -> str:
        """Format time range for display.

        Args:
            start_time: Start time
            end_time: End time

        Returns:
            Human-readable time range string
        """
        delta = end_time - start_time
        if delta.days == 0:
            return '24h'
        elif delta.days <= 7:
            return '7d'
        elif delta.days <= 30:
            return '30d'
        else:
            return '90d'

    # ========================================================================
    # User Story 4: Time-Series Metrics (T095-T100)
    # ========================================================================

    def get_time_series_metrics(self, time_range: str = '24h', metric_type: str = 'performance') -> Dict:
        """Retrieve time-series metrics data for chart visualization.

        Returns hourly data points for the specified time range.
        Automatically routes to raw vs aggregated tables based on age.

        Args:
            time_range: Time range ("24h", "7d", "30d", "90d")
            metric_type: Type of metrics ("performance", "usage", "both")

        Returns:
            Dictionary with time_range, interval, and data_points array
        """
        start_time, end_time = self._parse_time_range(time_range)

        logger.info(f'Time-series query: {time_range} ({metric_type})')

        # Determine interval (hourly for now)
        interval = 'hourly'

        # Query based on metric type
        if metric_type == 'performance':
            data_points = self._query_performance_time_series(start_time, end_time)
        elif metric_type == 'usage':
            data_points = self._query_usage_time_series(start_time, end_time)
        elif metric_type == 'both':
            # Merge performance and usage data points
            perf_points = self._query_performance_time_series(start_time, end_time)
            usage_points = self._query_usage_time_series(start_time, end_time)
            data_points = self._merge_time_series_data(perf_points, usage_points)
        else:
            data_points = []

        return {
            'time_range': time_range,
            'interval': interval,
            'data_points': data_points
        }

    def _query_performance_time_series(self, start_time: datetime, end_time: datetime) -> List[Dict]:
        """Query performance metrics time-series data.

        Returns hourly data points with performance metrics.
        Routes to raw or aggregated tables based on age.
        """
        if (datetime.utcnow() - start_time).days <= 7:
            # Query raw performance_metrics table
            return self._query_raw_performance_time_series(start_time, end_time)
        else:
            # Query aggregated_metrics table
            return self._query_aggregated_performance_time_series(start_time, end_time)

    def _query_usage_time_series(self, start_time: datetime, end_time: datetime) -> List[Dict]:
        """Query usage events time-series data.

        Returns hourly data points with usage metrics.
        Routes to raw or aggregated tables based on age.
        """
        if (datetime.utcnow() - start_time).days <= 7:
            # Query raw usage_events table
            return self._query_raw_usage_time_series(start_time, end_time)
        else:
            # Query aggregated_metrics table
            return self._query_aggregated_usage_time_series(start_time, end_time)

    def _query_raw_performance_time_series(self, start_time: datetime, end_time: datetime) -> List[Dict]:
        """Query raw performance metrics grouped by hour.

        Uses PostgreSQL date_trunc to bucket by hour.
        """
        try:
            # Query metrics grouped by hour
            results = self.db.query(
                func.date_trunc('hour', PerformanceMetric.timestamp).label('time_bucket'),
                func.avg(PerformanceMetric.response_time_ms).label('avg_response_time_ms'),
                func.count(PerformanceMetric.id).label('total_requests'),
                func.sum(
                    func.cast(PerformanceMetric.status_code >= 400, Integer)
                ).label('error_count')
            ).filter(
                and_(
                    PerformanceMetric.timestamp >= start_time,
                    PerformanceMetric.timestamp <= end_time
                )
            ).group_by('time_bucket').order_by('time_bucket').all()

            # Convert to data points
            data_points = []
            for row in results:
                total_requests = row.total_requests or 0
                error_count = row.error_count or 0
                error_rate = error_count / total_requests if total_requests > 0 else 0.0

                data_points.append({
                    'timestamp': row.time_bucket.isoformat() if row.time_bucket else '',
                    'avg_response_time_ms': float(row.avg_response_time_ms) if row.avg_response_time_ms else 0.0,
                    'total_requests': total_requests,
                    'error_rate': error_rate
                })

            return data_points
        except Exception as e:
            # Handle database connection errors gracefully
            logger.warning(f'Failed to query performance time-series: {e}')
            return []

    def _query_raw_usage_time_series(self, start_time: datetime, end_time: datetime) -> List[Dict]:
        """Query raw usage events grouped by hour.

        Uses PostgreSQL date_trunc to bucket by hour.
        """
        try:
            # Query events grouped by hour
            results = self.db.query(
                func.date_trunc('hour', UsageEvent.timestamp).label('time_bucket'),
                func.count(UsageEvent.id).label('total_events'),
                func.count(func.distinct(UsageEvent.user_id)).label('unique_users')
            ).filter(
                and_(
                    UsageEvent.timestamp >= start_time,
                    UsageEvent.timestamp <= end_time
                )
            ).group_by('time_bucket').order_by('time_bucket').all()

            # Convert to data points
            data_points = []
            for row in results:
                data_points.append({
                    'timestamp': row.time_bucket.isoformat() if row.time_bucket else '',
                    'total_events': row.total_events or 0,
                    'unique_users': row.unique_users or 0
                })

            return data_points
        except Exception as e:
            # Handle database connection errors gracefully
            logger.warning(f'Failed to query usage time-series: {e}')
            return []

    def _query_aggregated_performance_time_series(
        self,
        start_time: datetime,
        end_time: datetime
    ) -> List[Dict]:
        """Query aggregated performance metrics (for data >7 days old).

        Reads pre-computed hourly summaries from aggregated_metrics table.
        """
        try:
            results = self.db.query(AggregatedMetric).filter(
                and_(
                    AggregatedMetric.metric_type == 'performance',
                    AggregatedMetric.time_bucket >= start_time,
                    AggregatedMetric.time_bucket <= end_time
                )
            ).order_by(AggregatedMetric.time_bucket).all()

            # Convert aggregated values to data points
            data_points = []
            for agg in results:
                values = agg.aggregated_values
                data_points.append({
                    'timestamp': agg.time_bucket.isoformat(),
                    'avg_response_time_ms': values.get('avg_response_time_ms', 0.0),
                    'total_requests': values.get('total_requests', 0),
                    'error_rate': values.get('error_rate', 0.0)
                })

            return data_points
        except Exception as e:
            # Handle database connection errors gracefully
            logger.warning(f'Failed to query aggregated performance time-series: {e}')
            return []

    def _query_aggregated_usage_time_series(
        self,
        start_time: datetime,
        end_time: datetime
    ) -> List[Dict]:
        """Query aggregated usage metrics (for data >7 days old).

        Reads pre-computed hourly summaries from aggregated_metrics table.
        """
        try:
            results = self.db.query(AggregatedMetric).filter(
                and_(
                    AggregatedMetric.metric_type == 'usage',
                    AggregatedMetric.time_bucket >= start_time,
                    AggregatedMetric.time_bucket <= end_time
                )
            ).order_by(AggregatedMetric.time_bucket).all()

            # Convert aggregated values to data points
            data_points = []
            for agg in results:
                values = agg.aggregated_values
                data_points.append({
                    'timestamp': agg.time_bucket.isoformat(),
                    'total_events': values.get('total_events', 0),
                    'unique_users': values.get('unique_users', 0)
                })

            return data_points
        except Exception as e:
            # Handle database connection errors gracefully
            logger.warning(f'Failed to query aggregated usage time-series: {e}')
            return []

    def _merge_time_series_data(
        self,
        perf_points: List[Dict],
        usage_points: List[Dict]
    ) -> List[Dict]:
        """Merge performance and usage time-series data points.

        Combines data for the same timestamp into single data point.
        """
        # Create dictionary keyed by timestamp
        merged = {}

        # Add performance data
        for point in perf_points:
            timestamp = point['timestamp']
            merged[timestamp] = {
                'timestamp': timestamp,
                'avg_response_time_ms': point.get('avg_response_time_ms'),
                'total_requests': point.get('total_requests'),
                'error_rate': point.get('error_rate')
            }

        # Add usage data (merge if timestamp exists)
        for point in usage_points:
            timestamp = point['timestamp']
            if timestamp in merged:
                merged[timestamp]['total_events'] = point.get('total_events')
                merged[timestamp]['unique_users'] = point.get('unique_users')
            else:
                merged[timestamp] = {
                    'timestamp': timestamp,
                    'total_events': point.get('total_events'),
                    'unique_users': point.get('unique_users')
                }

        # Convert to sorted list
        sorted_points = sorted(merged.values(), key=lambda x: x['timestamp'])
        return sorted_points

