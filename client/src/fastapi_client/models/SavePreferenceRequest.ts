/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { PreferenceKey } from './PreferenceKey';
/**
 * Request body for saving preference.
 */
export type SavePreferenceRequest = {
    /**
     * Preference category
     */
    preference_key: PreferenceKey;
    /**
     * Preference data as JSON
     */
    preference_value: Record<string, any>;
};

