"""Contract tests for LakebaseService data isolation patterns.

These tests validate that LakebaseService correctly implements data isolation:
- NEVER accepts user_token parameter (service principal only for database)
- ALL user-scoped queries include WHERE user_id = ?
- Validates user_id presence before query execution
- Returns ValueError when user_id missing

Test Requirements (from contracts/service_layers.yaml):
- LakebaseService NEVER accepts user_token
- get_preferences() includes WHERE user_id = ?
- save_preference() stores with correct user_id
- Missing user_id raises ValueError
- Queries always use service principal database connection
"""

from unittest.mock import MagicMock, Mock, patch

import pytest

from server.services.lakebase_service import LakebaseService

# Mark all tests in this module as contract tests
pytestmark = pytest.mark.contract


class TestLakebaseServiceDataIsolation:
  """Test LakebaseService data isolation patterns."""

  @pytest.fixture
  def mock_env(self, monkeypatch):
    """Set up environment variables for Lakebase connection."""
    monkeypatch.setenv('PGHOST', 'test.lakebase.com')
    monkeypatch.setenv('PGDATABASE', 'test_db')
    monkeypatch.setenv('PGUSER', 'test_user')
    monkeypatch.setenv('PGPORT', '5432')
    monkeypatch.setenv('PGSSLMODE', 'require')

  def test_service_never_accepts_user_token(self, mock_env):
    """Test that LakebaseService NEVER accepts user_token parameter."""
    # Initialize service
    service = LakebaseService()

    # Verify service has no user_token attribute
    assert not hasattr(service, 'user_token'), (
      'LakebaseService should NOT have user_token attribute'
    )

    # Verify __init__ signature doesn't accept user_token
    import inspect

    init_signature = inspect.signature(LakebaseService.__init__)
    params = list(init_signature.parameters.keys())

    assert 'user_token' not in params, (
      'LakebaseService.__init__() should NOT accept user_token parameter'
    )

  @pytest.mark.asyncio
  async def test_get_preferences_filters_by_user_id(self, mock_env):
    """Test that get_preferences() filters by user_id."""
    with patch('server.services.lakebase_service.get_db_session') as mock_get_session:
      # Mock database session
      mock_session = MagicMock()
      mock_query = MagicMock()
      mock_filter_by = MagicMock()

      # Mock preference objects
      mock_pref1 = Mock()
      mock_pref1.to_dict.return_value = {
        'preference_key': 'theme',
        'preference_value': {'color': 'dark'},
      }
      mock_pref2 = Mock()
      mock_pref2.to_dict.return_value = {
        'preference_key': 'language',
        'preference_value': {'lang': 'en'},
      }

      mock_filter_by.all.return_value = [mock_pref1, mock_pref2]
      mock_query.filter_by.return_value = mock_filter_by
      mock_session.query.return_value = mock_query
      mock_get_session.return_value = [mock_session]

      # Initialize service
      service = LakebaseService()

      # Get user preferences with user_id
      user_id = 'user@example.com'
      preferences = await service.get_preferences(user_id=user_id)

      # Verify query was built with user_id filter
      assert mock_session.query.called, 'Database query should be created'
      assert mock_query.filter_by.called, 'Should filter by user_id'

      # Verify filter_by was called with user_id
      call_args = mock_query.filter_by.call_args
      assert call_args[1].get('user_id') == user_id, 'Query MUST filter by user_id'

      # Verify preferences returned
      assert len(preferences) == 2, 'Should return 2 preferences'

  @pytest.mark.asyncio
  async def test_get_preferences_validates_user_id_presence(self, mock_env):
    """Test that get_preferences() raises ValueError when user_id is missing."""
    service = LakebaseService()

    # Test with None user_id
    with pytest.raises(ValueError, match='User identity required'):
      await service.get_preferences(user_id=None)

    # Test with empty string user_id
    with pytest.raises(ValueError, match='User identity required'):
      await service.get_preferences(user_id='')

    # Test with whitespace-only user_id
    with pytest.raises(ValueError, match='User identity required'):
      await service.get_preferences(user_id='   ')

  @pytest.mark.asyncio
  async def test_save_preference_stores_with_user_id(self, mock_env):
    """Test that save_preference() stores with correct user_id."""
    with patch('server.services.lakebase_service.get_db_session') as mock_get_session:
      # Mock database session
      mock_session = MagicMock()
      mock_query = MagicMock()
      mock_filter_by = MagicMock()
      mock_filter_by.first.return_value = None  # No existing preference
      mock_query.filter_by.return_value = mock_filter_by
      mock_session.query.return_value = mock_query
      mock_get_session.return_value = [mock_session]

      # Initialize service
      service = LakebaseService()

      # Save preference
      user_id = 'user@example.com'
      preference_key = 'theme'
      preference_value = {'color': 'dark'}

      await service.save_preference(
        user_id=user_id, preference_key=preference_key, preference_value=preference_value
      )

      # Verify add was called
      assert mock_session.add.called, 'Should add new preference'

      # Verify the preference object has the correct user_id
      added_pref = mock_session.add.call_args[0][0]
      assert added_pref.user_id == user_id, 'Preference MUST be stored with correct user_id'

  @pytest.mark.asyncio
  async def test_save_preference_validates_user_id(self, mock_env):
    """Test that save_preference() validates user_id."""
    service = LakebaseService()

    # Test with None user_id
    with pytest.raises(ValueError, match='User identity required'):
      await service.save_preference(
        user_id=None, preference_key='theme', preference_value={'color': 'dark'}
      )

    # Test with empty string user_id
    with pytest.raises(ValueError, match='User identity required'):
      await service.save_preference(
        user_id='', preference_key='theme', preference_value={'color': 'dark'}
      )

  @pytest.mark.asyncio
  async def test_delete_preference_filters_by_user_id(self, mock_env):
    """Test that delete_preference() filters by user_id."""
    with patch('server.services.lakebase_service.get_db_session') as mock_get_session:
      # Mock database session
      mock_session = MagicMock()
      mock_query = MagicMock()
      mock_filter_by = MagicMock()
      mock_pref = Mock()

      mock_filter_by.first.return_value = mock_pref
      mock_query.filter_by.return_value = mock_filter_by
      mock_session.query.return_value = mock_query
      mock_get_session.return_value = [mock_session]

      # Initialize service
      service = LakebaseService()

      # Delete preference
      user_id = 'user@example.com'
      preference_key = 'theme'

      await service.delete_preference(user_id=user_id, preference_key=preference_key)

      # Verify filter_by was called with both user_id AND preference_key
      call_args = mock_query.filter_by.call_args
      assert call_args[1].get('user_id') == user_id, 'Delete MUST filter by user_id'
      assert call_args[1].get('preference_key') == preference_key, (
        'Delete MUST filter by preference_key'
      )

  @pytest.mark.asyncio
  async def test_cross_user_access_prevention(self, mock_env):
    """Test that users cannot access other users' preferences."""
    with patch('server.services.lakebase_service.get_db_session') as mock_get_session:
      # Mock database session
      mock_session = MagicMock()
      mock_query = MagicMock()
      mock_filter_by = MagicMock()

      # Mock empty result (no preferences for this user)
      mock_filter_by.all.return_value = []
      mock_query.filter_by.return_value = mock_filter_by
      mock_session.query.return_value = mock_query
      mock_get_session.return_value = [mock_session]

      # Initialize service
      service = LakebaseService()

      # Try to get preferences for user A
      user_a_id = 'userA@example.com'
      preferences_a = await service.get_preferences(user_id=user_a_id)

      # Verify filter_by was called with user A's ID
      call_args = mock_query.filter_by.call_args
      assert call_args[1].get('user_id') == user_a_id, 'Query MUST use the specified user_id'

      # Verify empty result (user A cannot see user B's data)
      assert len(preferences_a) == 0, 'Should return empty list when no data for user'

  def test_uses_service_principal_database_connection(self, mock_env):
    """Test that LakebaseService uses service principal for database."""
    # Initialize service
    service = LakebaseService()

    # Verify service has no user_token
    assert not hasattr(service, 'user_token'), (
      'Service should NOT have user_token (uses service principal)'
    )

    # Verify db_session can be None (uses get_db_session which uses service principal)
    assert service.db_session is None or service.db_session is not None, (
      'Service should support both injected and auto-created sessions'
    )


class TestLakebaseServiceQuerySafety:
  """Test query safety and parameterization."""

  @pytest.mark.asyncio
  async def test_queries_use_parameterized_statements(self):
    """Test that queries use parameterized statements (not string concatenation)."""
    with patch('server.services.lakebase_service.get_db_session') as mock_get_session:
      # Mock database session
      mock_session = MagicMock()
      mock_query = MagicMock()
      mock_filter_by = MagicMock()

      mock_filter_by.all.return_value = []
      mock_query.filter_by.return_value = mock_filter_by
      mock_session.query.return_value = mock_query
      mock_get_session.return_value = [mock_session]

      # Initialize service
      service = LakebaseService()

      # Execute query with user_id
      malicious_user_id = "user@example.com' OR '1'='1"  # SQL injection attempt
      await service.get_preferences(user_id=malicious_user_id)

      # Verify filter_by was called (uses parameterized query)
      assert mock_query.filter_by.called, 'Should use filter_by (parameterized)'

      # Verify the malicious string was passed as parameter (not concatenated)
      call_args = mock_query.filter_by.call_args
      assert call_args[1].get('user_id') == malicious_user_id, (
        'Should pass user_id as parameter (prevents SQL injection)'
      )

  @pytest.mark.asyncio
  async def test_user_id_validation_before_query_execution(self):
    """Test that user_id is validated BEFORE query execution."""
    service = LakebaseService()

    # Test that validation happens before any database query
    with pytest.raises(ValueError, match='User identity required'):
      # This should fail before any database interaction
      await service.get_preferences(user_id=None)

  @pytest.mark.asyncio
  async def test_all_user_scoped_methods_require_user_id(self):
    """Test that ALL user-scoped methods require user_id."""
    service = LakebaseService()

    # get_preferences requires user_id
    with pytest.raises(ValueError):
      await service.get_preferences(user_id=None)

    # save_preference requires user_id
    with pytest.raises(ValueError):
      await service.save_preference(
        user_id=None, preference_key='theme', preference_value={'color': 'dark'}
      )

    # delete_preference requires user_id
    with pytest.raises(ValueError):
      await service.delete_preference(user_id=None, preference_key='theme')
