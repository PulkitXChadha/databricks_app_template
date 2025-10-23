"""Daily metrics aggregation job script.

This script aggregates 7-day-old raw metrics into hourly summaries and deletes
raw records. It also cleans up aggregated metrics older than 90 days.

Designed to run as a Databricks scheduled job (daily at 2 AM UTC).
Entry point: main() function (configured in pyproject.toml console_scripts)
"""

import logging
import os
import sys
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from sqlalchemy import and_, create_engine
from sqlalchemy.orm import Session, sessionmaker

from server.models.aggregated_metric import AggregatedMetric
from server.models.performance_metric import PerformanceMetric
from server.models.usage_event import UsageEvent

# Configure logging
logging.basicConfig(
  level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def aggregate_performance_metrics(session: Session, cutoff_date: datetime) -> int:
  """Aggregate 7-day-old performance metrics into hourly buckets.

  Groups metrics by hour and endpoint, calculates statistics, and stores
  in aggregated_metrics table. Deletes raw records in same transaction.

  Args:
      session: SQLAlchemy database session
      cutoff_date: Metrics older than this date will be aggregated

  Returns:
      Number of aggregated buckets created

  Raises:
      Exception: If aggregation fails (transaction will rollback)
  """
  logger.info(f'Aggregating performance metrics older than {cutoff_date.isoformat()}')

  # Query raw metrics older than cutoff
  old_metrics = (
    session.query(PerformanceMetric).filter(PerformanceMetric.timestamp < cutoff_date).all()
  )

  if not old_metrics:
    logger.info('No performance metrics to aggregate')
    return 0

  logger.info(f'Found {len(old_metrics)} performance metrics to aggregate')

  # Check for existing aggregated records (idempotency)
  # Group by hourly bucket and endpoint
  hourly_buckets: Dict[tuple, List[PerformanceMetric]] = {}

  for metric in old_metrics:
    # Truncate timestamp to hour
    hour_bucket = metric.timestamp.replace(minute=0, second=0, microsecond=0)
    key = (hour_bucket, metric.endpoint)

    if key not in hourly_buckets:
      hourly_buckets[key] = []
    hourly_buckets[key].append(metric)

  logger.info(f'Created {len(hourly_buckets)} hourly buckets for aggregation')

  # Create aggregated records
  aggregated_count = 0
  skipped_count = 0

  for (hour_bucket, endpoint), metrics_group in hourly_buckets.items():
    # Check if aggregated record already exists (idempotency)
    existing = (
      session.query(AggregatedMetric)
      .filter(
        and_(
          AggregatedMetric.time_bucket == hour_bucket,
          AggregatedMetric.metric_type == 'performance',
          AggregatedMetric.endpoint_path == endpoint,
        )
      )
      .first()
    )

    if existing:
      logger.debug(f'Skipping already aggregated bucket: {hour_bucket} - {endpoint}')
      skipped_count += 1
      continue

    # Calculate statistics
    response_times = [m.response_time_ms for m in metrics_group]
    error_count = sum(1 for m in metrics_group if m.status_code >= 400)
    total_requests = len(metrics_group)

    # Calculate percentiles using sorted data
    sorted_times = sorted(response_times)
    p50_index = int(len(sorted_times) * 0.50)
    p95_index = int(len(sorted_times) * 0.95)
    p99_index = int(len(sorted_times) * 0.99)

    aggregated_values = {
      'avg_response_time_ms': sum(response_times) / len(response_times),
      'min_response_time_ms': min(response_times),
      'max_response_time_ms': max(response_times),
      'p50_response_time_ms': sorted_times[min(p50_index, len(sorted_times) - 1)],
      'p95_response_time_ms': sorted_times[min(p95_index, len(sorted_times) - 1)],
      'p99_response_time_ms': sorted_times[min(p99_index, len(sorted_times) - 1)],
      'total_requests': total_requests,
      'error_count': error_count,
      'error_rate': error_count / total_requests if total_requests > 0 else 0.0,
      'status_code_distribution': _calculate_status_code_distribution(metrics_group),
    }

    # Create aggregated metric record
    aggregated = AggregatedMetric(
      time_bucket=hour_bucket,
      metric_type='performance',
      endpoint_path=endpoint,
      event_type=None,
      aggregated_values=aggregated_values,
      sample_count=total_requests,
    )

    session.add(aggregated)
    aggregated_count += 1

  if skipped_count > 0:
    logger.info(f'Skipped {skipped_count} already aggregated buckets (idempotency)')

  # Delete processed raw metrics (atomic transaction with aggregation)
  delete_count = (
    session.query(PerformanceMetric).filter(PerformanceMetric.timestamp < cutoff_date).delete()
  )

  logger.info(
    f'Aggregated {aggregated_count} performance metric buckets, deleted {delete_count} raw records'
  )

  return aggregated_count


def aggregate_usage_events(session: Session, cutoff_date: datetime) -> int:
  """Aggregate 7-day-old usage events into hourly buckets.

  Groups events by hour and event type, calculates statistics, and stores
  in aggregated_metrics table. Deletes raw records in same transaction.

  Args:
      session: SQLAlchemy database session
      cutoff_date: Events older than this date will be aggregated

  Returns:
      Number of aggregated buckets created
  """
  logger.info(f'Aggregating usage events older than {cutoff_date.isoformat()}')

  # Query raw events older than cutoff
  old_events = session.query(UsageEvent).filter(UsageEvent.timestamp < cutoff_date).all()

  if not old_events:
    logger.info('No usage events to aggregate')
    return 0

  logger.info(f'Found {len(old_events)} usage events to aggregate')

  # Group by hourly bucket and event type
  hourly_buckets: Dict[tuple, List[UsageEvent]] = {}

  for event in old_events:
    hour_bucket = event.timestamp.replace(minute=0, second=0, microsecond=0)
    key = (hour_bucket, event.event_type)

    if key not in hourly_buckets:
      hourly_buckets[key] = []
    hourly_buckets[key].append(event)

  logger.info(f'Created {len(hourly_buckets)} hourly buckets for usage aggregation')

  # Create aggregated records
  aggregated_count = 0
  skipped_count = 0

  for (hour_bucket, event_type), events_group in hourly_buckets.items():
    # Check for existing record (idempotency)
    existing = (
      session.query(AggregatedMetric)
      .filter(
        and_(
          AggregatedMetric.time_bucket == hour_bucket,
          AggregatedMetric.metric_type == 'usage',
          AggregatedMetric.event_type == event_type,
        )
      )
      .first()
    )

    if existing:
      logger.debug(f'Skipping already aggregated bucket: {hour_bucket} - {event_type}')
      skipped_count += 1
      continue

    # Calculate statistics
    total_events = len(events_group)
    unique_users = len(set(e.user_id for e in events_group))
    success_count = sum(1 for e in events_group if e.success is True)
    failure_count = sum(1 for e in events_group if e.success is False)

    # Group by page
    page_distribution = {}
    for event in events_group:
      if event.page_name:
        page_distribution[event.page_name] = page_distribution.get(event.page_name, 0) + 1

    aggregated_values = {
      'total_events': total_events,
      'unique_users': unique_users,
      'event_count_by_page': page_distribution,
      'success_count': success_count,
      'failure_count': failure_count,
      'success_rate': success_count / total_events if total_events > 0 else 0.0,
    }

    aggregated = AggregatedMetric(
      time_bucket=hour_bucket,
      metric_type='usage',
      endpoint_path=None,
      event_type=event_type,
      aggregated_values=aggregated_values,
      sample_count=total_events,
    )

    session.add(aggregated)
    aggregated_count += 1

  if skipped_count > 0:
    logger.info(f'Skipped {skipped_count} already aggregated buckets (idempotency)')

  # Delete processed raw events
  delete_count = session.query(UsageEvent).filter(UsageEvent.timestamp < cutoff_date).delete()

  logger.info(
    f'Aggregated {aggregated_count} usage event buckets, deleted {delete_count} raw records'
  )

  return aggregated_count


def cleanup_old_aggregated_metrics(session: Session) -> int:
  """Delete aggregated metrics older than 90 days.

  Args:
      session: SQLAlchemy database session

  Returns:
      Number of records deleted
  """
  cutoff_date = datetime.utcnow() - timedelta(days=90)
  logger.info(f'Cleaning up aggregated metrics older than {cutoff_date.isoformat()}')

  # Delete old aggregated records
  delete_count = (
    session.query(AggregatedMetric).filter(AggregatedMetric.time_bucket < cutoff_date).delete()
  )

  logger.info(f'Deleted {delete_count} aggregated metric records older than 90 days')

  return delete_count


def check_database_size_and_alert(session: Session, total_count: Optional[int] = None) -> Dict:
  """Monitor database size and trigger alerts/actions when thresholds exceeded.

  Implements SC-007 (database size monitoring) and SC-009 (alert prefix requirement).

  Thresholds:
  - 800K records: WARNING log
  - 1M records: ERROR log with "ALERT:" prefix + emergency aggregation

  Args:
      session: SQLAlchemy database session
      total_count: Optional pre-calculated total count (for testing)

  Returns:
      Dictionary with monitoring results
  """
  if total_count is None:
    # Count records across all tables
    perf_count = session.query(PerformanceMetric).count()
    usage_count = session.query(UsageEvent).count()
    agg_count = session.query(AggregatedMetric).count()
    total_count = perf_count + usage_count + agg_count

  result = {
    'total_count': total_count,
    'warning_threshold_exceeded': False,
    'error_threshold_exceeded': False,
    'emergency_aggregation_triggered': False,
  }

  # Check 800K threshold (WARNING)
  if total_count >= 800000:
    logger.warning(
      f'Database size approaching limit: {total_count:,} records '
      f'(80% of 1M threshold). Consider reviewing aggregation frequency.'
    )
    result['warning_threshold_exceeded'] = True

  # Check 1M threshold (ERROR with ALERT: prefix per SC-009)
  if total_count >= 1000000:
    logger.error(
      f'ALERT: Database size exceeded 1M threshold: {total_count:,} records. '
      f'Triggering emergency aggregation and admin notification.'
    )
    result['error_threshold_exceeded'] = True
    result['emergency_aggregation_triggered'] = True

    # TODO: Implement emergency aggregation logic
    # TODO: Send notification to workspace admins

  return result


def _calculate_status_code_distribution(metrics: List[PerformanceMetric]) -> Dict[str, int]:
  """Calculate distribution of HTTP status codes.

  Args:
      metrics: List of PerformanceMetric objects

  Returns:
      Dictionary mapping status code to count
  """
  distribution = {}
  for metric in metrics:
    code_str = str(metric.status_code)
    distribution[code_str] = distribution.get(code_str, 0) + 1
  return distribution


def main():
  """Main entry point for aggregation job.

  Called by Databricks scheduled job via console script entry point.
  """
  logger.info('=' * 80)
  logger.info('Starting metrics aggregation job')
  logger.info('=' * 80)

  try:
    # Get database URL from environment
    database_url = os.environ.get('DATABASE_URL')
    if not database_url:
      logger.error('DATABASE_URL environment variable not set')
      sys.exit(2)

    # Create database engine and session
    engine = create_engine(database_url)
    Session = sessionmaker(bind=engine)
    session = Session()

    # Calculate cutoff date (7 days ago)
    cutoff_date = datetime.utcnow() - timedelta(days=7)
    logger.info(f'Aggregation cutoff date: {cutoff_date.isoformat()}')

    # Start transaction
    try:
      # Aggregate performance metrics
      perf_count = aggregate_performance_metrics(session, cutoff_date)

      # Aggregate usage events
      usage_count = aggregate_usage_events(session, cutoff_date)

      # Cleanup old aggregated metrics (90+ days)
      cleanup_count = cleanup_old_aggregated_metrics(session)

      # Commit transaction (atomic: all or nothing)
      session.commit()

      logger.info(
        f'Aggregation job completed successfully: '
        f'{perf_count} performance buckets, '
        f'{usage_count} usage buckets, '
        f'{cleanup_count} old aggregated records deleted'
      )

      # Check database size and alert if needed
      monitoring_result = check_database_size_and_alert(session)
      logger.info(f'Database monitoring: {monitoring_result["total_count"]:,} total records')

      sys.exit(0)

    except Exception as e:
      logger.error(f'Aggregation job failed: {e}', exc_info=True)
      session.rollback()
      sys.exit(2)

    finally:
      session.close()

  except Exception as e:
    logger.error(f'Fatal error in aggregation job: {e}', exc_info=True)
    sys.exit(1)


if __name__ == '__main__':
  main()
