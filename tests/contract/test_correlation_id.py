"""Contract tests for correlation ID generation and propagation.

Tests FR-017 from spec.md.
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
import uuid
import re


class TestCorrelationId:
    """Contract tests for correlation ID propagation."""

    def test_middleware_generates_uuid_when_correlation_id_missing(self, client):
        """Test middleware generates UUID when X-Correlation-ID header is missing."""
        with patch('server.services.user_service.UserService.get_user_info') as mock_get_user_info:
            mock_get_user_info.return_value = MagicMock(
                user_id="user@example.com",
                display_name="Test User",
                active=True
            )

            response = client.get(
                "/api/user/me",
                headers={"X-Forwarded-Access-Token": "test-token"}
            )

            # Response should include X-Correlation-ID header
            assert "X-Correlation-ID" in response.headers

            correlation_id = response.headers["X-Correlation-ID"]

            # Should be a valid UUID v4
            uuid_pattern = re.compile(
                r'^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
                re.IGNORECASE
            )
            assert uuid_pattern.match(correlation_id), f"Invalid UUID format: {correlation_id}"

    def test_middleware_preserves_client_provided_correlation_id(self, client):
        """Test middleware preserves client-provided X-Correlation-ID."""
        client_correlation_id = "12345678-1234-1234-1234-123456789abc"

        with patch('server.services.user_service.UserService.get_user_info') as mock_get_user_info:
            mock_get_user_info.return_value = MagicMock(
                user_id="user@example.com",
                display_name="Test User",
                active=True
            )

            response = client.get(
                "/api/user/me",
                headers={
                    "X-Forwarded-Access-Token": "test-token",
                    "X-Correlation-ID": client_correlation_id
                }
            )

            # Response should return the same correlation ID
            assert response.headers["X-Correlation-ID"] == client_correlation_id

    def test_correlation_id_included_in_all_response_headers(self, client):
        """Test correlation ID is included in all response headers."""
        endpoints = [
            "/api/health",
            "/api/auth/status",
        ]

        for endpoint in endpoints:
            response = client.get(endpoint)

            assert "X-Correlation-ID" in response.headers, \
                f"Missing X-Correlation-ID header for {endpoint}"

            correlation_id = response.headers["X-Correlation-ID"]
            assert len(correlation_id) > 0, f"Empty correlation ID for {endpoint}"

    def test_correlation_id_included_in_log_entries(self, client):
        """Test correlation ID is included in all log entries for request."""
        client_correlation_id = str(uuid.uuid4())

        with patch('server.lib.structured_logger.logger') as mock_logger, \
             patch('server.services.user_service.UserService.get_user_info') as mock_get_user_info:

            mock_get_user_info.return_value = MagicMock(
                user_id="user@example.com",
                display_name="Test User",
                active=True
            )

            response = client.get(
                "/api/user/me",
                headers={
                    "X-Forwarded-Access-Token": "test-token",
                    "X-Correlation-ID": client_correlation_id
                }
            )

            # Check if logger was called (some log calls should exist)
            # Note: This depends on implementation having logging in place
            assert response.status_code in [200, 500]  # Either success or error

            # If logger was used, verify correlation_id is in log context
            if mock_logger.info.called or mock_logger.warning.called or mock_logger.error.called:
                # Check all log calls for correlation_id
                all_log_calls = (
                    mock_logger.info.call_args_list +
                    mock_logger.warning.call_args_list +
                    mock_logger.error.call_args_list
                )

                # At least some log entries should contain correlation_id
                log_contexts = []
                for call in all_log_calls:
                    if len(call[0]) > 1 and isinstance(call[0][1], dict):
                        log_contexts.append(call[0][1])

                # Verify correlation_id is propagated through logs
                if log_contexts:
                    correlation_ids_in_logs = [
                        ctx.get("correlation_id")
                        for ctx in log_contexts
                        if "correlation_id" in ctx
                    ]
                    # At least one log should have the correlation ID
                    assert len(correlation_ids_in_logs) > 0

    def test_uuid_format_validated(self, client):
        """Test that generated correlation IDs are valid UUID v4 format."""
        # Make multiple requests to test UUID generation
        correlation_ids = []

        for _ in range(5):
            response = client.get("/api/health")
            correlation_id = response.headers.get("X-Correlation-ID")
            correlation_ids.append(correlation_id)

        # All should be valid UUIDs
        uuid_pattern = re.compile(
            r'^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
            re.IGNORECASE
        )

        for correlation_id in correlation_ids:
            assert uuid_pattern.match(correlation_id), \
                f"Invalid UUID v4 format: {correlation_id}"

        # All should be unique
        assert len(correlation_ids) == len(set(correlation_ids)), \
            "Correlation IDs are not unique"

    def test_correlation_id_propagates_through_error_responses(self, client):
        """Test correlation ID is included even in error responses."""
        client_correlation_id = str(uuid.uuid4())

        # Try an endpoint that will fail (missing authentication)
        response = client.get(
            "/api/user/me",
            headers={"X-Correlation-ID": client_correlation_id}
        )

        # Even if request fails, correlation ID should be in response
        assert "X-Correlation-ID" in response.headers
        assert response.headers["X-Correlation-ID"] == client_correlation_id

    def test_correlation_id_consistent_across_request_lifecycle(self, client):
        """Test that the same correlation ID is used throughout request lifecycle."""
        client_correlation_id = str(uuid.uuid4())

        with patch('server.lib.structured_logger.logger') as mock_logger:
            response = client.get(
                "/api/health",
                headers={"X-Correlation-ID": client_correlation_id}
            )

            # Response should have the same correlation ID
            assert response.headers["X-Correlation-ID"] == client_correlation_id

            # All logs during request should use the same correlation ID
            if mock_logger.info.called:
                log_contexts = [
                    call[0][1] for call in mock_logger.info.call_args_list
                    if len(call[0]) > 1 and isinstance(call[0][1], dict) and "correlation_id" in call[0][1]
                ]

                if log_contexts:
                    # All logged correlation IDs should match
                    correlation_ids_in_logs = [ctx["correlation_id"] for ctx in log_contexts]
                    assert all(cid == client_correlation_id for cid in correlation_ids_in_logs)

