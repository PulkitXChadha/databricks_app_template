"""Contract tests for retry logic with exponential backoff and error handling.

Tests FR-018, FR-019, FR-025, NFR-006 from spec.md.
"""

import time
from unittest.mock import patch

import pytest
from databricks.sdk.errors import DatabricksError

from server.lib.auth import AuthenticationError, RateLimitError, with_auth_retry


class TestRetryLogic:
  """Contract tests for retry logic and error handling."""

  @pytest.mark.asyncio
  async def test_retry_triggers_on_authentication_failures(self):
    """Test that retry triggers on authentication failures (3 attempts)."""
    attempt_count = 0

    @with_auth_retry
    async def failing_auth_call():
      nonlocal attempt_count
      attempt_count += 1
      # Simulate authentication failure
      error = DatabricksError(message='Authentication failed', error_code='UNAUTHENTICATED')
      raise error

    with pytest.raises(AuthenticationError):
      await failing_auth_call()

    # Should have attempted 3 times (initial + 2 retries within 5 sec timeout)
    assert attempt_count >= 3

  @pytest.mark.asyncio
  async def test_exponential_backoff_delays(self):
    """Test exponential backoff delays (100ms, 200ms, 400ms)."""
    attempt_times = []

    @with_auth_retry
    async def failing_auth_call():
      attempt_times.append(time.time())
      error = DatabricksError(message='Authentication failed', error_code='UNAUTHENTICATED')
      raise error

    with pytest.raises(AuthenticationError):
      await failing_auth_call()

    # Calculate delays between attempts
    if len(attempt_times) >= 2:
      delays = []
      for i in range(1, len(attempt_times)):
        delay_ms = (attempt_times[i] - attempt_times[i - 1]) * 1000
        delays.append(delay_ms)

      # Verify delays are approximately exponential (with tolerance)
      # Expected: ~100ms, ~200ms, ~400ms
      if len(delays) >= 1:
        assert 50 <= delays[0] <= 200, f'First delay should be ~100ms, got {delays[0]}ms'
      if len(delays) >= 2:
        assert 150 <= delays[1] <= 350, f'Second delay should be ~200ms, got {delays[1]}ms'

  @pytest.mark.asyncio
  async def test_total_retry_time_less_than_5_seconds(self):
    """Test that total retry time is less than 5 seconds."""
    start_time = time.time()

    @with_auth_retry
    async def failing_auth_call():
      error = DatabricksError(message='Authentication failed', error_code='UNAUTHENTICATED')
      raise error

    with pytest.raises(AuthenticationError):
      await failing_auth_call()

    total_time = time.time() - start_time

    # Total time should be less than 5 seconds (NFR-006)
    assert total_time < 5.0, f'Total retry time {total_time}s exceeds 5 second limit'

  @pytest.mark.asyncio
  async def test_rate_limiting_fails_immediately_without_retry(self):
    """Test that rate limiting (429) fails immediately without retry."""
    attempt_count = 0

    @with_auth_retry
    async def rate_limited_call():
      nonlocal attempt_count
      attempt_count += 1
      # Simulate rate limit error
      error = DatabricksError(
        message='Too many requests', error_code='RESOURCE_EXHAUSTED', status_code=429
      )
      raise error

    with pytest.raises(RateLimitError):
      await rate_limited_call()

    # Should only attempt once (no retries for rate limiting)
    assert attempt_count == 1

  @pytest.mark.asyncio
  async def test_retry_count_logged_correctly(self):
    """Test that retry count is logged correctly."""
    with patch('server.lib.auth.logger') as mock_logger:

      @with_auth_retry
      async def failing_auth_call():
        error = DatabricksError(message='Authentication failed', error_code='UNAUTHENTICATED')
        raise error

      with pytest.raises(AuthenticationError):
        await failing_auth_call()

      # Verify logger was called with retry attempts
      warning_calls = [
        call
        for call in mock_logger.warning.call_args_list
        if len(call[0]) > 0 and 'auth.retry_attempt' in str(call[0][0])
      ]

      # Should have logged retry attempts
      assert len(warning_calls) > 0

  @pytest.mark.asyncio
  async def test_final_error_returned_after_max_retries(self):
    """Test that final error is returned after max retries."""

    @with_auth_retry
    async def failing_auth_call():
      error = DatabricksError(message='Authentication failed', error_code='UNAUTHENTICATED')
      raise error

    with pytest.raises(AuthenticationError) as exc_info:
      await failing_auth_call()

    # Verify the final exception contains authentication error message
    assert 'Authentication failed' in str(exc_info.value)

  @pytest.mark.asyncio
  async def test_successful_call_after_retries(self):
    """Test that successful call after transient failures works."""
    attempt_count = 0

    @with_auth_retry
    async def eventually_successful_call():
      nonlocal attempt_count
      attempt_count += 1

      # Fail first 2 attempts, succeed on 3rd
      if attempt_count < 3:
        error = DatabricksError(message='Transient failure', error_code='UNAUTHENTICATED')
        raise error

      return 'success'

    result = await eventually_successful_call()

    assert result == 'success'
    assert attempt_count == 3

  @pytest.mark.asyncio
  async def test_multiple_concurrent_requests_retry_independently(self):
    """Test that multiple concurrent requests retry independently (no coordination)."""
    attempt_counts = {'req1': 0, 'req2': 0}

    @with_auth_retry
    async def failing_request(request_id: str):
      attempt_counts[request_id] += 1
      error = DatabricksError(message='Auth failed', error_code='UNAUTHENTICATED')
      raise error

    # Run two concurrent requests
    import asyncio

    results = await asyncio.gather(
      failing_request('req1'), failing_request('req2'), return_exceptions=True
    )

    # Both requests should have retried independently
    assert attempt_counts['req1'] >= 3
    assert attempt_counts['req2'] >= 3

    # Both should have failed with AuthenticationError
    assert all(isinstance(r, AuthenticationError) for r in results)

  @pytest.mark.asyncio
  async def test_circuit_breaker_opens_after_consecutive_failures(self):
    """Test that circuit breaker opens after too many consecutive failures."""
    from server.lib.auth import auth_circuit_breaker

    # Reset circuit breaker state
    auth_circuit_breaker.consecutive_failures = 0
    auth_circuit_breaker.state = 'closed'

    # Simulate many consecutive failures (threshold is 10)
    for _ in range(12):
      auth_circuit_breaker.record_failure()

    # Circuit breaker should be open
    assert auth_circuit_breaker.is_open() is True
    assert auth_circuit_breaker.state == 'open'

  @pytest.mark.asyncio
  async def test_circuit_breaker_resets_on_success(self):
    """Test that circuit breaker resets on successful request."""
    from server.lib.auth import auth_circuit_breaker

    # Set some failures
    auth_circuit_breaker.consecutive_failures = 5
    auth_circuit_breaker.state = 'closed'

    # Record success
    auth_circuit_breaker.record_success()

    # Circuit breaker should reset
    assert auth_circuit_breaker.consecutive_failures == 0
    assert auth_circuit_breaker.state == 'closed'

  @pytest.mark.asyncio
  async def test_different_error_types_handled_identically(self):
    """Test that expired, invalid, and malformed tokens are handled identically."""
    error_types = [
      DatabricksError(message='Token expired', error_code='UNAUTHENTICATED'),
      DatabricksError(message='Token invalid', error_code='UNAUTHENTICATED'),
      DatabricksError(message='Token malformed', error_code='INVALID_ARGUMENT'),
    ]

    for error in error_types:
      attempt_count = 0

      @with_auth_retry
      async def failing_call():
        nonlocal attempt_count
        attempt_count += 1
        raise error

      with pytest.raises(AuthenticationError):
        await failing_call()

      # All error types should trigger retries
      assert attempt_count >= 3
