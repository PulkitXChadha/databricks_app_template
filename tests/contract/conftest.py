"""Shared test fixtures and utilities for contract tests.

Note: Common fixtures are now defined in tests/conftest.py and are
automatically available to all contract tests.
"""

# Contract tests can use fixtures from tests/conftest.py:
# - app, client, test_client
# - mock_db_session, mock_db_session_with_data
# - mock_user_identity, mock_user_identity_a, mock_user_identity_b
# - user_token, user_a_token, user_b_token
# - mock_env
# - correlation_id, sample_preferences
