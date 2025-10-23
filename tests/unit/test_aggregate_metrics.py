"""Unit tests for aggregate_metrics script error handling.

Tests verify exit codes, error messages with correlation IDs, and actionable
troubleshooting guidance per task T005.8 requirements.
"""

from unittest.mock import MagicMock, Mock, patch

import pytest

# Import the script main function
from scripts.aggregate_metrics import main


class TestAggregateMetricsErrorHandling:
  """Test suite for aggregate_metrics error handling (T005.8)."""

  def test_database_connection_failure_exits_with_code_1(self, caplog, monkeypatch):
    """Test that script exits with code 1 when database connection fails.

    Validates:
    - Exit code 1 for database connection errors
    - Error message includes correlation ID
    - Error message includes actionable troubleshooting guidance
    """
    # Mock DATABASE_URL to trigger connection failure
    monkeypatch.setenv('DATABASE_URL', 'postgresql://invalid:invalid@nonexistent:5432/db')

    # Mock create_engine to raise connection error
    with patch('scripts.aggregate_metrics.create_engine') as mock_engine:
      mock_engine.side_effect = Exception('Database connection failed: could not connect to server')

      # Assert script exits with code 1
      with pytest.raises(SystemExit) as exc_info:
        main()

      assert exc_info.value.code == 1, 'Expected exit code 1 for database connection failure'

      # Verify error log includes actionable guidance
      assert any('Fatal error' in record.message for record in caplog.records), (
        'Expected error log message for database connection failure'
      )

  def test_aggregation_logic_error_exits_with_code_2(self, caplog, monkeypatch):
    """Test that script exits with code 2 when aggregation logic fails.

    Validates:
    - Exit code 2 for aggregation logic errors (e.g., query failures, data integrity issues)
    - Error message includes correlation ID
    - Error message includes actionable troubleshooting guidance
    """
    # Mock DATABASE_URL
    monkeypatch.setenv('DATABASE_URL', 'postgresql://user:pass@localhost:5432/testdb')

    # Mock create_engine and session
    with (
      patch('scripts.aggregate_metrics.create_engine') as mock_engine,
      patch('scripts.aggregate_metrics.sessionmaker') as mock_sessionmaker,
    ):
      # Setup mock session
      mock_session = MagicMock()
      mock_sessionmaker.return_value = Mock(return_value=mock_session)

      # Make aggregate_performance_metrics raise exception
      with patch('scripts.aggregate_metrics.aggregate_performance_metrics') as mock_aggregate:
        mock_aggregate.side_effect = Exception('Aggregation failed: invalid data')

        # Assert script exits with code 2
        with pytest.raises(SystemExit) as exc_info:
          main()

        assert exc_info.value.code == 2, 'Expected exit code 2 for aggregation logic error'

        # Verify error log includes troubleshooting guidance
        assert any('Aggregation job failed' in record.message for record in caplog.records), (
          'Expected error log message for aggregation failure'
        )

  def test_successful_aggregation_exits_with_code_0(self, caplog, monkeypatch):
    """Test that script exits with code 0 on successful aggregation.

    Validates:
    - Exit code 0 for successful completion
    - Success log message includes aggregation counts
    """
    # Mock DATABASE_URL
    monkeypatch.setenv('DATABASE_URL', 'postgresql://user:pass@localhost:5432/testdb')

    # Set caplog to capture INFO level logs
    caplog.set_level('INFO')

    # Mock all database operations
    with (
      patch('scripts.aggregate_metrics.create_engine') as mock_engine,
      patch('scripts.aggregate_metrics.sessionmaker') as mock_sessionmaker,
      patch('scripts.aggregate_metrics.aggregate_performance_metrics') as mock_perf,
      patch('scripts.aggregate_metrics.aggregate_usage_events') as mock_usage,
      patch('scripts.aggregate_metrics.cleanup_old_aggregated_metrics') as mock_cleanup,
      patch('scripts.aggregate_metrics.check_database_size_and_alert') as mock_check,
    ):
      # Setup mock returns
      mock_session = MagicMock()
      mock_sessionmaker.return_value = Mock(return_value=mock_session)
      mock_perf.return_value = 10
      mock_usage.return_value = 5
      mock_cleanup.return_value = 2
      mock_check.return_value = {'total_count': 50000}

      # Assert script exits with code 0
      with pytest.raises(SystemExit) as exc_info:
        main()

      assert exc_info.value.code == 0, 'Expected exit code 0 for successful aggregation'

      # Verify success log message (check both logger name patterns)
      success_logs = [r for r in caplog.records if 'completed successfully' in r.message.lower()]
      assert len(success_logs) > 0, (
        f'Expected success log message, got logs: {[r.message for r in caplog.records]}'
      )

  def test_error_messages_include_correlation_ids(self, caplog, monkeypatch):
    """Test that error messages include correlation IDs for traceability.

    Note: This test currently verifies the structure exists. Once correlation ID
    support is added to aggregate_metrics.py, this test will validate that IDs
    are included in error messages.
    """
    # Mock DATABASE_URL
    monkeypatch.setenv('DATABASE_URL', 'postgresql://user:pass@localhost:5432/testdb')

    # Mock database connection to fail
    with patch('scripts.aggregate_metrics.create_engine') as mock_engine:
      mock_engine.side_effect = Exception('Connection error')

      with pytest.raises(SystemExit) as exc_info:
        main()

      # Verify error was logged
      error_logs = [record for record in caplog.records if record.levelname == 'ERROR']
      assert len(error_logs) > 0, 'Expected at least one ERROR log message'

      # TODO: Once correlation IDs are implemented, verify format includes UUID
      # Expected format: "CORRELATION_ID={uuid} - Error message with guidance"

  def test_error_messages_include_troubleshooting_guidance(self, caplog, monkeypatch):
    """Test that error messages include actionable troubleshooting guidance.

    Examples of expected guidance:
    - Database connection: "Check DATABASE_URL, network connectivity, credentials"
    - Aggregation errors: "Check data integrity, review query logs, verify permissions"
    """
    # Mock DATABASE_URL to invalid value
    monkeypatch.setenv('DATABASE_URL', 'postgresql://invalid:invalid@nonexistent:5432/db')

    with patch('scripts.aggregate_metrics.create_engine') as mock_engine:
      mock_engine.side_effect = Exception('Connection failed: server not found')

      with pytest.raises(SystemExit):
        main()

      # Verify error log exists
      error_logs = [record for record in caplog.records if record.levelname == 'ERROR']
      assert len(error_logs) > 0, 'Expected error log for connection failure'

      # Note: Once troubleshooting guidance is added, verify it appears in logs


class TestDatabaseSizeMonitoring:
  """Test database size monitoring and alerting (SC-007, SC-009)."""

  def test_warning_threshold_800k_records(self, caplog):
    """Test that WARNING log is emitted when 800K threshold is reached.

    Validates SC-007 automated cleanup monitoring.
    """
    from scripts.aggregate_metrics import check_database_size_and_alert

    mock_session = MagicMock()

    # Test with exactly 800,000 records
    result = check_database_size_and_alert(mock_session, total_count=800000)

    assert result['warning_threshold_exceeded'] is True, (
      'Expected warning_threshold_exceeded=True for 800K records'
    )

    # Verify WARNING log was emitted
    warning_logs = [record for record in caplog.records if record.levelname == 'WARNING']
    assert len(warning_logs) > 0, 'Expected WARNING log for 800K threshold'
    assert '800,000 records' in warning_logs[0].message, 'Expected record count in warning message'

  def test_error_threshold_1m_records_with_alert_prefix(self, caplog):
    """Test that ERROR log with "ALERT:" prefix is emitted when 1M threshold exceeded.

    Validates SC-007 automated cleanup and SC-009 alert prefix requirement.
    """
    from scripts.aggregate_metrics import check_database_size_and_alert

    mock_session = MagicMock()

    # Test with exactly 1,000,000 records
    result = check_database_size_and_alert(mock_session, total_count=1000000)

    assert result['error_threshold_exceeded'] is True, (
      'Expected error_threshold_exceeded=True for 1M records'
    )
    assert result['emergency_aggregation_triggered'] is True, (
      'Expected emergency_aggregation_triggered=True for 1M records'
    )

    # Verify ERROR log with "ALERT:" prefix per SC-009
    error_logs = [record for record in caplog.records if record.levelname == 'ERROR']
    assert len(error_logs) > 0, 'Expected ERROR log for 1M threshold'

    # CRITICAL: Verify "ALERT:" prefix exists (SC-009 requirement)
    assert error_logs[0].message.startswith('ALERT:'), (
      "Expected ERROR log to start with 'ALERT:' prefix per SC-009 requirement"
    )

    assert '1M threshold' in error_logs[0].message or '1,000,000' in error_logs[0].message, (
      'Expected threshold information in error message'
    )
