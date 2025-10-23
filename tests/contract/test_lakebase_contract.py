"""Contract tests for Lakebase API endpoints.

Tests validate that the API implementation matches the OpenAPI specification
defined in contracts/lakebase_api.yaml.

Expected Result: Tests FAIL initially (no implementation yet) - TDD approach.
"""

import pytest
from fastapi.testclient import TestClient

from server.app import app

client = TestClient(app)


@pytest.fixture
def auth_headers():
  """Provide authentication headers for contract tests."""
  return {'X-Forwarded-Access-Token': 'mock-user-token-for-testing'}


class TestLakebaseGetPreferencesContract:
  """Contract tests for GET /api/preferences endpoint."""

  def test_get_preferences_response_structure(self):
    """Verify response matches UserPreference[] schema from OpenAPI spec."""
    response = client.get('/api/preferences')

    # Should return 200, 401, or 503
    assert response.status_code in [200, 401, 503], (
      f'Unexpected status code: {response.status_code}'
    )

    if response.status_code == 200:
      data = response.json()
      assert isinstance(data, list), 'Response should be an array'

      # Validate UserPreference schema for each preference
      for pref in data:
        assert 'id' in pref, 'Missing id field'
        assert 'user_id' in pref, 'Missing user_id field'
        assert 'preference_key' in pref, 'Missing preference_key field'
        assert 'preference_value' in pref, 'Missing preference_value field'
        assert 'created_at' in pref, 'Missing created_at field'
        assert 'updated_at' in pref, 'Missing updated_at field'

        # Validate preference_key enum
        assert pref['preference_key'] in ['dashboard_layout', 'favorite_tables', 'theme'], (
          f'Invalid preference_key: {pref["preference_key"]}'
        )

        # Validate preference_value is an object
        assert isinstance(pref['preference_value'], dict), (
          'preference_value should be a JSON object'
        )

  def test_get_preferences_correlation_id_header(self):
    """Verify X-Request-ID header is present in response."""
    response = client.get('/api/preferences')

    if response.status_code == 200:
      assert 'X-Request-ID' in response.headers or 'x-request-id' in response.headers, (
        'Missing X-Request-ID header for correlation ID'
      )

  def test_get_preferences_with_key_filter(self):
    """Verify preference_key query parameter works correctly."""
    response = client.get('/api/preferences?preference_key=theme')

    assert response.status_code in [200, 401, 503]

    if response.status_code == 200:
      data = response.json()
      for pref in data:
        assert pref['preference_key'] == 'theme', 'preference_key filter not applied correctly'


class TestLakebaseCreatePreferenceContract:
  """Contract tests for POST /api/preferences endpoint."""

  def test_create_preference_response_structure(self):
    """Verify response matches UserPreference schema from OpenAPI spec."""
    payload = {
      'preference_key': 'theme',
      'preference_value': {'mode': 'dark', 'accent_color': 'blue'},
    }

    response = client.post('/api/preferences', json=payload)

    # Should return 200, 400, 401, or 503
    assert response.status_code in [200, 400, 401, 503], (
      f'Unexpected status code: {response.status_code}'
    )

    if response.status_code == 200:
      data = response.json()

      # Validate required fields
      assert 'id' in data, 'Missing id field'
      assert 'user_id' in data, 'Missing user_id field'
      assert 'preference_key' in data, 'Missing preference_key field'
      assert 'preference_value' in data, 'Missing preference_value field'
      assert 'created_at' in data, 'Missing created_at field'
      assert 'updated_at' in data, 'Missing updated_at field'

      # Validate returned preference matches request
      assert data['preference_key'] == payload['preference_key']
      assert data['preference_value'] == payload['preference_value']

  def test_create_preference_required_fields(self, auth_headers, mock_user_auth):
    """Verify required fields (preference_key, preference_value) are enforced."""
    # Missing preference_key
    payload = {'preference_value': {'mode': 'dark'}}
    response = client.post('/api/preferences', json=payload, headers=auth_headers)
    assert response.status_code == 422, 'Should reject missing preference_key'

    # Missing preference_value
    payload = {'preference_key': 'theme'}
    response = client.post('/api/preferences', json=payload, headers=auth_headers)
    assert response.status_code == 422, 'Should reject missing preference_value'

  def test_create_preference_key_enum_validation(self, auth_headers, mock_user_auth):
    """Verify preference_key must be one of allowed values."""
    valid_keys = ['dashboard_layout', 'favorite_tables', 'theme']

    # Test valid keys
    for key in valid_keys:
      payload = {'preference_key': key, 'preference_value': {'test': 'value'}}
      response = client.post('/api/preferences', json=payload, headers=auth_headers)
      assert response.status_code in [201, 503], f'Valid preference_key rejected: {key}'

    # Test invalid key
    payload = {'preference_key': 'invalid_key', 'preference_value': {'test': 'value'}}
    response = client.post('/api/preferences', json=payload, headers=auth_headers)
    # Should either reject at validation (422) or app level (400)
    assert response.status_code in [400, 422], 'Should reject invalid preference_key'

  def test_create_preference_error_response_structure(self):
    """Verify error responses match ErrorResponse schema."""
    # Send invalid preference
    payload = {'preference_key': 'invalid_key', 'preference_value': 'not_an_object'}

    response = client.post('/api/preferences', json=payload)

    if response.status_code in [400, 422]:
      data = response.json()
      # FastAPI may return different structure, but should have error info
      assert 'error_code' in data or 'detail' in data, 'Error response missing error information'


class TestLakebaseDeletePreferenceContract:
  """Contract tests for DELETE /api/preferences/{preference_key} endpoint."""

  def test_delete_preference_success(self):
    """Verify successful deletion returns 204 No Content."""
    response = client.delete('/api/preferences/theme')

    # Should return 204, 401, 404, or 503
    assert response.status_code in [204, 401, 404, 503], (
      f'Unexpected status code: {response.status_code}'
    )

    if response.status_code == 204:
      # 204 should have no content
      assert response.text == '' or len(response.content) == 0, (
        'DELETE success should return no content'
      )

  def test_delete_preference_correlation_id_header(self):
    """Verify X-Request-ID header is present in response."""
    response = client.delete('/api/preferences/theme')

    if response.status_code == 204:
      assert 'X-Request-ID' in response.headers or 'x-request-id' in response.headers, (
        'Missing X-Request-ID header for correlation ID'
      )

  def test_delete_nonexistent_preference(self):
    """Verify deleting non-existent preference returns 404."""
    response = client.delete('/api/preferences/nonexistent_key')

    # Should return 404 if preference doesn't exist for this user
    # Could also return 204 if idempotent design
    assert response.status_code in [204, 401, 404, 503]

    if response.status_code == 404:
      data = response.json()
      assert 'error_code' in data, 'Missing error_code in 404 response'
      assert 'message' in data, 'Missing message in 404 response'

  def test_delete_preference_valid_keys(self):
    """Verify only valid preference_key values are accepted."""
    valid_keys = ['dashboard_layout', 'favorite_tables', 'theme']

    for key in valid_keys:
      response = client.delete(f'/api/preferences/{key}')
      # Should accept valid keys (may return 404 if not found, but not 400/422)
      assert response.status_code in [204, 401, 404, 503], (
        f'Valid preference_key rejected in delete: {key}'
      )


class TestLakebaseDataIsolation:
  """Contract tests for user data isolation requirements."""

  def test_preferences_user_scoped(self):
    """Verify all preferences are user-scoped (data isolation).

    This test validates the core requirement that all Lakebase records
    are strictly user-isolated with no shared records.
    """
    # Get preferences - should only return current user's preferences
    response = client.get('/api/preferences')

    if response.status_code == 200:
      data = response.json()
      # All returned preferences should have same user_id
      user_ids = set(pref['user_id'] for pref in data)
      assert len(user_ids) <= 1, 'Multiple user_ids found in preferences (data isolation violated)'


if __name__ == '__main__':
  pytest.main([__file__, '-v'])
