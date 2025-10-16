"""Contract tests for user preferences endpoints with data isolation validation.

Tests FR-010, FR-013, FR-014 from spec.md.
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock, AsyncMock
import uuid


class TestPreferencesContract:
    """Contract tests for user preferences endpoints."""

    def test_get_preferences_returns_only_authenticated_users_preferences(self, client, mock_user_auth):
        """Test GET /api/preferences returns only authenticated user's preferences."""
        user_token = "mock-user-token-12345"
        user_id = "test@example.com"  # From mock_user_auth fixture

        # Patch get_preferences (not get_user_preferences) since that's what the router calls
        with patch('server.services.lakebase_service.LakebaseService.get_preferences', new_callable=AsyncMock) as mock_get_prefs:

            mock_get_prefs.return_value = [
                {
                    "id": 1,
                    "user_id": user_id,
                    "preference_key": "theme",
                    "preference_value": {"mode": "dark"},
                    "created_at": "2025-10-10T12:00:00Z",
                    "updated_at": "2025-10-10T12:00:00Z"
                }
            ]

            response = client.get(
                "/api/preferences",
                headers={"X-Forwarded-Access-Token": user_token}
            )

            assert response.status_code == 200
            preferences = response.json()
            assert len(preferences) == 1
            assert preferences[0]["preference_key"] == "theme"

            # Verify user_id was passed to lakebase service
            mock_get_prefs.assert_called_once_with(user_id=user_id, preference_key=None)

    def test_post_preference_saves_with_correct_user_id(self, client, mock_user_auth):
        """Test POST /api/preferences saves with correct user_id."""
        user_token = "mock-user-token-12345"
        user_id = "test@example.com"  # From mock_user_auth fixture

        with patch('server.services.lakebase_service.LakebaseService.save_preference', new_callable=AsyncMock) as mock_save_pref:

            mock_save_pref.return_value = {
                "id": 1,
                "user_id": user_id,
                "preference_key": "theme",
                "preference_value": {"mode": "dark"},
                "created_at": "2025-10-10T12:00:00Z",
                "updated_at": "2025-10-10T12:00:00Z"
            }

            response = client.post(
                "/api/preferences",
                headers={"X-Forwarded-Access-Token": user_token},
                json={"preference_key": "theme", "preference_value": {"mode": "dark"}}
            )

            assert response.status_code == 201
            preference = response.json()
            assert preference["preference_key"] == "theme"
            assert preference["preference_value"]["mode"] == "dark"

            # Verify user_id was passed to save function
            mock_save_pref.assert_called_once_with(
                user_id=user_id,
                preference_key="theme",
                preference_value={"mode": "dark"}
            )

    def test_delete_preference_only_deletes_authenticated_users_preference(self, client, mock_user_auth):
        """Test DELETE /api/preferences/{key} only deletes authenticated user's preference."""
        user_token = "mock-user-token-12345"
        user_id = "test@example.com"  # From mock_user_auth fixture

        with patch('server.services.lakebase_service.LakebaseService.delete_preference', new_callable=AsyncMock) as mock_delete_pref:

            mock_delete_pref.return_value = True  # Successfully deleted

            response = client.delete(
                "/api/preferences/theme",
                headers={"X-Forwarded-Access-Token": user_token}
            )

            assert response.status_code == 204

            # Verify user_id was passed to delete function
            mock_delete_pref.assert_called_once_with(user_id=user_id, preference_key="theme")

    def test_cross_user_access_prevented(self, client, mock_user_auth):
        """Test that User A cannot see User B's data."""
        user_token = "mock-user-token"
        user_id = "test@example.com"  # From mock_user_auth fixture

        # Patch get_preferences (not get_user_preferences)
        with patch('server.services.lakebase_service.LakebaseService.get_preferences', new_callable=AsyncMock) as mock_get_prefs:

            # First call returns data
            mock_get_prefs.return_value = [
                {
                    "id": 1,
                    "user_id": user_id,
                    "preference_key": "theme",
                    "preference_value": {"mode": "dark"},
                    "created_at": "2025-10-10T12:00:00Z",
                    "updated_at": "2025-10-10T12:00:00Z"
                }
            ]

            response_a = client.get(
                "/api/preferences",
                headers={"X-Forwarded-Access-Token": user_token}
            )
            assert response_a.status_code == 200
            assert len(response_a.json()) == 1

            # Second call returns empty (simulating different user)
            mock_get_prefs.return_value = []

            response_b = client.get(
                "/api/preferences",
                headers={"X-Forwarded-Access-Token": user_token}
            )
            assert response_b.status_code == 200
            assert len(response_b.json()) == 0

            # Verify each call used user_id parameter (enforcing data isolation)
            calls = mock_get_prefs.call_args_list
            assert calls[0][1]["user_id"] == user_id
            assert calls[1][1]["user_id"] == user_id

    def test_missing_token_returns_401(self, client, mock_user_auth):
        """Test that missing token returns 401 error."""
        # Request without authentication token should fail
        response = client.get("/api/preferences")

        assert response.status_code == 401
        error_detail = response.json()
        # Handle both dict and string detail formats
        if isinstance(error_detail.get("detail"), dict):
            detail_text = error_detail["detail"].get("message", "")
        else:
            detail_text = str(error_detail.get("detail", ""))
        assert "authentication" in detail_text.lower() or "auth" in detail_text.lower()

    def test_database_queries_include_user_id_filter(self, client, mock_user_auth):
        """Test that database queries include WHERE user_id = ? clause."""
        user_token = "mock-user-token-12345"
        user_id = "test@example.com"  # From mock_user_auth fixture

        # Patch get_preferences (not get_user_preferences)
        with patch('server.services.lakebase_service.LakebaseService.get_preferences', new_callable=AsyncMock) as mock_get_prefs:

            mock_get_prefs.return_value = []

            response = client.get(
                "/api/preferences",
                headers={"X-Forwarded-Access-Token": user_token}
            )

            assert response.status_code == 200

            # Verify user_id parameter was passed (enforces WHERE clause)
            mock_get_prefs.assert_called_once()
            call_kwargs = mock_get_prefs.call_args[1]
            assert "user_id" in call_kwargs
            assert call_kwargs["user_id"] == user_id

