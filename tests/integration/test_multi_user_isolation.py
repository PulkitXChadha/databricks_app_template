"""
Integration test for multi-user data isolation.

Tests that users can only access their own data in Lakebase (user_preferences)
and that Unity Catalog enforces table-level permissions automatically.

**Test Requirements** (from tasks.md T036):
1. Use 2 distinct Databricks user accounts (or mock WorkspaceClient.current_user.me())
2. User A creates preference, User B cannot see it
3. User B creates preference with same key, both users see only their own
4. Unity Catalog queries return only user-accessible tables
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from fastapi.testclient import TestClient
from server.app import app
from server.models.user_preference import UserPreference
from server.lib.database import get_db_session
from sqlalchemy.orm import Session


class TestMultiUserIsolation:
    """Test suite for multi-user data isolation across Lakebase and Unity Catalog."""
    
    @pytest.fixture
    def client(self):
        """Create test client for FastAPI app."""
        return TestClient(app)
    
    @pytest.fixture
    def mock_user_a(self):
        """Mock User A authentication context."""
        user = Mock()
        user.user_name = "user-a@company.com"
        user.user_id = "user-a-id"
        user.email = "user-a@company.com"
        return user
    
    @pytest.fixture
    def mock_user_b(self):
        """Mock User B authentication context."""
        user = Mock()
        user.user_name = "user-b@company.com"
        user.user_id = "user-b-id"
        user.email = "user-b@company.com"
        return user
    
    @pytest.fixture(autouse=True)
    def setup_and_teardown(self):
        """Clean up test data before and after each test."""
        session: Session = next(get_db_session())
        try:
            # Clean up any existing test data
            session.query(UserPreference).filter(
                UserPreference.user_id.in_(["user-a@company.com", "user-b@company.com"])
            ).delete(synchronize_session=False)
            session.commit()
            yield
        finally:
            # Clean up after test
            session.query(UserPreference).filter(
                UserPreference.user_id.in_(["user-a@company.com", "user-b@company.com"])
            ).delete(synchronize_session=False)
            session.commit()
            session.close()
    
    def test_lakebase_preference_isolation(self, client, mock_user_a, mock_user_b):
        """
        Test that user preferences are isolated by user_id in Lakebase.
        
        Acceptance Criteria:
        1. User A creates preference with key='theme', value='dark'
        2. User B queries GET /api/preferences with their auth context
        3. Assert User B receives empty array (no User A preferences visible)
        4. User B creates preference with same key='theme', value='light'
        5. Assert User A and User B each see only their own preference
        """
        with patch('server.routers.lakebase.get_current_user_id') as mock_get_user:
            # Step 1: User A creates preference
            mock_get_user.return_value = mock_user_a.user_name
            response_a_create = client.post(
                "/api/preferences",
                json={"preference_key": "theme", "preference_value": {"mode": "dark"}}
            )
            assert response_a_create.status_code == 200
            # Response is UserPreferenceResponse object, not a message
            preference_data = response_a_create.json()
            assert "preference_key" in preference_data
            assert preference_data["preference_key"] == "theme"
            
            # Step 2-3: User B queries preferences, should see empty array
            mock_get_user.return_value = mock_user_b.user_name
            response_b_get = client.get("/api/preferences")
            assert response_b_get.status_code == 200
            # Response is a list directly, not {"preferences": [...]}
            preferences_b = response_b_get.json()
            assert len(preferences_b) == 0, "User B should not see User A's preferences"
            
            # Step 4: User B creates preference with same key
            response_b_create = client.post(
                "/api/preferences",
                json={"preference_key": "theme", "preference_value": {"mode": "light"}}
            )
            assert response_b_create.status_code == 200
            
            # Step 5: Verify User A sees only their preference
            mock_get_user.return_value = mock_user_a.user_name
            response_a_get = client.get("/api/preferences")
            assert response_a_get.status_code == 200
            # Response is a list directly
            preferences_a = response_a_get.json()
            assert len(preferences_a) == 1
            assert preferences_a[0]["preference_key"] == "theme"
            assert preferences_a[0]["preference_value"]["mode"] == "dark"
            
            # Step 5: Verify User B sees only their preference
            mock_get_user.return_value = mock_user_b.user_name
            response_b_get_final = client.get("/api/preferences")
            assert response_b_get_final.status_code == 200
            preferences_b_final = response_b_get_final.json()["preferences"]
            assert len(preferences_b_final) == 1
            assert preferences_b_final[0]["preference_key"] == "theme"
            assert preferences_b_final[0]["preference_value"]["mode"] == "light"
    
    def test_lakebase_delete_isolation(self, client, mock_user_a, mock_user_b):
        """
        Test that users cannot delete other users' preferences.
        
        Acceptance Criteria:
        1. User A creates preference 'dashboard_layout'
        2. User B attempts to delete User A's preference
        3. Assert deletion has no effect (User A's preference still exists)
        4. User B can only delete their own preferences
        """
        with patch('server.routers.lakebase.get_current_user_id') as mock_get_user:
            # Step 1: User A creates preference
            mock_get_user.return_value = mock_user_a.user_name
            client.post(
                "/api/preferences",
                json={"preference_key": "dashboard_layout", "preference_value": {"columns": 3}}
            )
            
            # Step 2-3: User B attempts to delete User A's preference
            mock_get_user.return_value = mock_user_b.user_name
            response_b_delete = client.delete("/api/preferences/dashboard_layout")
            # Returns 204 (no content) even if preference doesn't exist for this user
            # This is acceptable as delete is idempotent - no User B preference is deleted
            assert response_b_delete.status_code == 204
            
            # Verify User A's preference still exists (isolation working correctly)
            mock_get_user.return_value = mock_user_a.user_name
            response_a_get = client.get("/api/preferences")
            # Response is a list directly
            preferences_a = response_a_get.json()
            assert len(preferences_a) == 1
            assert preferences_a[0]["preference_key"] == "dashboard_layout"
    
    @patch('server.services.unity_catalog_service.UnityCatalogService.list_tables')
    def test_unity_catalog_permission_isolation(self, mock_list_tables, client, mock_user_a, mock_user_b):
        """
        Test that Unity Catalog enforces table permissions per user.
        
        Acceptance Criteria:
        1. User A queries Unity Catalog tables
        2. Mock returns only tables User A has access to
        3. User B queries Unity Catalog tables
        4. Mock returns different set of tables for User B
        5. Verify each user sees only their accessible tables
        """
        with patch('server.routers.unity_catalog.get_current_user_id') as mock_get_user:
            # Step 1-2: User A queries tables
            mock_get_user.return_value = mock_user_a.user_name
            mock_list_tables.return_value = [
                {
                    "catalog_name": "main",
                    "schema_name": "samples",
                    "table_name": "user_a_data",
                    "columns": [{"name": "id", "data_type": "int", "nullable": False}],
                    "owner": "user-a@company.com",
                    "access_level": "READ"
                }
            ]
            response_a = client.get("/api/unity-catalog/tables?catalog=main&schema=samples")
            assert response_a.status_code == 200
            # Response is a list directly, not {"tables": [...]}
            tables_a = response_a.json()
            assert len(tables_a) == 1
            assert tables_a[0]["table_name"] == "user_a_data"
            
            # Step 3-4: User B queries tables
            mock_get_user.return_value = mock_user_b.user_name
            mock_list_tables.return_value = [
                {
                    "catalog_name": "main",
                    "schema_name": "samples",
                    "table_name": "user_b_data",
                    "columns": [{"name": "id", "data_type": "int", "nullable": False}],
                    "owner": "user-b@company.com",
                    "access_level": "READ"
                }
            ]
            response_b = client.get("/api/unity-catalog/tables?catalog=main&schema=samples")
            assert response_b.status_code == 200
            # Response is a list directly
            tables_b = response_b.json()
            assert len(tables_b) == 1
            assert tables_b[0]["table_name"] == "user_b_data"
            
            # Step 5: Verify isolation - User B cannot see User A's table
            assert "user_a_data" not in [t["table_name"] for t in tables_b]
    
    def test_preference_update_isolation(self, client, mock_user_a, mock_user_b):
        """
        Test that users cannot update other users' preferences.
        
        Acceptance Criteria:
        1. User A creates preference 'favorite_tables'
        2. User B creates same preference key with different value
        3. User A updates their preference
        4. Assert User B's preference unchanged
        5. User B updates their preference
        6. Assert User A's preference unchanged
        """
        with patch('server.routers.lakebase.get_current_user_id') as mock_get_user:
            # Step 1: User A creates preference
            mock_get_user.return_value = mock_user_a.user_name
            client.post(
                "/api/preferences",
                json={"preference_key": "favorite_tables", "preference_value": {"tables": ["table_a"]}}
            )
            
            # Step 2: User B creates same key with different value
            mock_get_user.return_value = mock_user_b.user_name
            client.post(
                "/api/preferences",
                json={"preference_key": "favorite_tables", "preference_value": {"tables": ["table_b"]}}
            )
            
            # Step 3: User A updates their preference
            mock_get_user.return_value = mock_user_a.user_name
            client.post(
                "/api/preferences",
                json={"preference_key": "favorite_tables", "preference_value": {"tables": ["table_a", "table_c"]}}
            )
            
            # Step 4: Verify User B's preference unchanged
            mock_get_user.return_value = mock_user_b.user_name
            response_b = client.get("/api/preferences")
            # Response is a list directly
            preferences_b = response_b.json()
            assert len(preferences_b[0]["preference_value"]["tables"]) == 1
            assert "table_b" in preferences_b[0]["preference_value"]["tables"]
            assert "table_a" not in preferences_b[0]["preference_value"]["tables"]
            
            # Step 5: User B updates their preference
            client.post(
                "/api/preferences",
                json={"preference_key": "favorite_tables", "preference_value": {"tables": ["table_b", "table_d"]}}
            )
            
            # Step 6: Verify User A's preference unchanged
            mock_get_user.return_value = mock_user_a.user_name
            response_a = client.get("/api/preferences")
            # Response is a list directly
            preferences_a = response_a.json()
            assert len(preferences_a[0]["preference_value"]["tables"]) == 2
            assert "table_a" in preferences_a[0]["preference_value"]["tables"]
            assert "table_c" in preferences_a[0]["preference_value"]["tables"]
            assert "table_d" not in preferences_a[0]["preference_value"]["tables"]


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])

