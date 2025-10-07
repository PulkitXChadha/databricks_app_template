/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { SavePreferenceRequest } from '../models/SavePreferenceRequest';
import type { UserPreferenceResponse } from '../models/UserPreferenceResponse';
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';
export class LakebaseService {
    /**
     * Get Preferences
     * Get user preferences (user-scoped, data isolated).
     *
     * Query Parameters:
     * preference_key: Specific preference key (optional, returns all if omitted)
     *
     * Returns:
     * List of user preferences
     *
     * Raises:
     * 503: Database unavailable (EC-002)
     * @param preferenceKey
     * @returns UserPreferenceResponse Successful Response
     * @throws ApiError
     */
    public static getPreferencesApiPreferencesGet(
        preferenceKey?: (string | null),
    ): CancelablePromise<Array<UserPreferenceResponse>> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/preferences',
            query: {
                'preference_key': preferenceKey,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Save Preference
     * Create or update user preference (user-scoped).
     *
     * Request Body:
     * preference_key: Preference category (dashboard_layout, favorite_tables, theme)
     * preference_value: Preference data as JSON
     *
     * Returns:
     * Saved preference
     *
     * Raises:
     * 400: Invalid preference data
     * 503: Database unavailable (EC-002)
     * @param requestBody
     * @returns UserPreferenceResponse Successful Response
     * @throws ApiError
     */
    public static savePreferenceApiPreferencesPost(
        requestBody: SavePreferenceRequest,
    ): CancelablePromise<UserPreferenceResponse> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/preferences',
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Delete Preference
     * Delete user preference (user-scoped).
     *
     * Path Parameters:
     * preference_key: Preference key to delete
     *
     * Returns:
     * 204 No Content on success
     *
     * Raises:
     * 404: Preference not found for this user
     * 503: Database unavailable (EC-002)
     * @param preferenceKey
     * @returns void
     * @throws ApiError
     */
    public static deletePreferenceApiPreferencesPreferenceKeyDelete(
        preferenceKey: string,
    ): CancelablePromise<void> {
        return __request(OpenAPI, {
            method: 'DELETE',
            url: '/api/preferences/{preference_key}',
            path: {
                'preference_key': preferenceKey,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
}
