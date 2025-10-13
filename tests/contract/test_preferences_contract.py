"""Contract tests for user preferences endpoints with data isolation validation.

Tests FR-010, FR-013, FR-014 from spec.md.
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock, AsyncMock
import uuid


class TestPreferencesContract:
    """Contract tests for user preferences endpoints."""

    def test_get_preferences_returns_only_authenticated_users_preferences(self, client):
        """Test GET /api/preferences returns only authenticated user's preferences."""
        user_token = "mock-user-token-12345"
        user_id = "user-a@example.com"

        with patch('server.services.user_service.UserService.get_user_id', new_callable=AsyncMock) as mock_get_user_id, \
             patch('server.services.lakebase_service.LakebaseService.get_user_preferences', new_callable=AsyncMock) as mock_get_prefs:

            mock_get_user_id.return_value = user_id
            mock_get_prefs.return_value = [
                {
                    "preference_key": "theme",
                    "preference_value": "dark",
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
            mock_get_prefs.assert_called_once_with(user_id=user_id)

    def test_post_preference_saves_with_correct_user_id(self, client):
        """Test POST /api/preferences saves with correct user_id."""
        user_token = "mock-user-token-12345"
        user_id = "user-a@example.com"

        with patch('server.services.user_service.UserService.get_user_id', new_callable=AsyncMock) as mock_get_user_id, \
             patch('server.services.lakebase_service.LakebaseService.save_user_preference', new_callable=AsyncMock) as mock_save_pref, \
             patch('server.services.lakebase_service.LakebaseService.get_preference', new_callable=AsyncMock) as mock_get_pref:

            mock_get_user_id.return_value = user_id
            mock_get_pref.return_value = {
                "preference_key": "theme",
                "preference_value": "dark",
                "created_at": "2025-10-10T12:00:00Z",
                "updated_at": "2025-10-10T12:00:00Z"
            }

            response = client.post(
                "/api/preferences",
                headers={"X-Forwarded-Access-Token": user_token},
                json={"preference_key": "theme", "preference_value": "dark"}
            )

            assert response.status_code == 201
            preference = response.json()
            assert preference["preference_key"] == "theme"
            assert preference["preference_value"] == "dark"

            # Verify user_id was passed to save function
            mock_save_pref.assert_called_once_with(
                user_id=user_id,
                key="theme",
                value="dark"
            )

    def test_delete_preference_only_deletes_authenticated_users_preference(self, client):
        """Test DELETE /api/preferences/{key} only deletes authenticated user's preference."""
        user_token = "mock-user-token-12345"
        user_id = "user-a@example.com"

        with patch('server.services.user_service.UserService.get_user_id', new_callable=AsyncMock) as mock_get_user_id, \
             patch('server.services.lakebase_service.LakebaseService.delete_preference', new_callable=AsyncMock) as mock_delete_pref:

            mock_get_user_id.return_value = user_id

            response = client.delete(
                "/api/preferences/theme",
                headers={"X-Forwarded-Access-Token": user_token}
            )

            assert response.status_code == 204

            # Verify user_id was passed to delete function
            mock_delete_pref.assert_called_once_with(user_id=user_id, key="theme")

    def test_cross_user_access_prevented(self, client):
        """Test that User A cannot see User B's data."""
        user_a_token = "mock-user-a-token"
        user_b_token = "mock-user-b-token"
        user_a_id = "user-a@example.com"
        user_b_id = "user-b@example.com"

        with patch('server.services.user_service.UserService.get_user_id', new_callable=AsyncMock) as mock_get_user_id, \
             patch('server.services.lakebase_service.LakebaseService.get_user_preferences', new_callable=AsyncMock) as mock_get_prefs:

            # User A saves a preference
            mock_get_user_id.return_value = user_a_id
            mock_get_prefs.return_value = [
                {"preference_key": "theme", "preference_value": "dark"}
            ]

            response_a = client.get(
                "/api/preferences",
                headers={"X-Forwarded-Access-Token": user_a_token}
            )
            assert response_a.status_code == 200
            assert len(response_a.json()) == 1

            # User B should see empty list (not User A's preferences)
            mock_get_user_id.return_value = user_b_id
            mock_get_prefs.return_value = []

            response_b = client.get(
                "/api/preferences",
                headers={"X-Forwarded-Access-Token": user_b_token}
            )
            assert response_b.status_code == 200
            assert len(response_b.json()) == 0

            # Verify each call used correct user_id
            calls = mock_get_prefs.call_args_list
            assert calls[0][1]["user_id"] == user_a_id
            assert calls[1][1]["user_id"] == user_b_id

    def test_missing_token_returns_401(self, client):
        """Test that missing token returns 401 error."""
        with patch('server.services.user_service.UserService.get_user_id', new_callable=AsyncMock) as mock_get_user_id:
            from fastapi import HTTPException
            mock_get_user_id.side_effect = HTTPException(status_code=401, detail="User authentication required")

            response = client.get("/api/preferences")

            assert response.status_code == 401
            assert "authentication required" in response.json()["detail"].lower()

    def test_database_queries_include_user_id_filter(self, client):
        """Test that database queries include WHERE user_id = ? clause."""
        user_token = "mock-user-token-12345"
        user_id = "user-a@example.com"

        with patch('server.services.user_service.UserService.get_user_id', new_callable=AsyncMock) as mock_get_user_id, \
             patch('server.services.lakebase_service.LakebaseService.get_user_preferences', new_callable=AsyncMock) as mock_get_prefs:

            mock_get_user_id.return_value = user_id
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

