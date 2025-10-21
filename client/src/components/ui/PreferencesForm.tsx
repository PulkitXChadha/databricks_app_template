/**
 * PreferencesForm Component
 *
 * CRUD form for user preferences stored in Lakebase.
 */

import React, { useState, useEffect } from "react";
import { Button, Alert, Typography } from "designbricks";
import { Skeleton } from "@/components/ui/skeleton";
import { usageTracker } from "@/services/usageTracker";

interface UserPreference {
  id: number;
  user_id: string;
  preference_key: string;
  preference_value: Record<string, any>;
  created_at: string;
  updated_at: string;
}

type PreferenceKey = "dashboard_layout" | "favorite_tables" | "theme";

interface PreferencesFormProps {
  preferences?: UserPreference[];
  loading?: boolean;
  error?: string | null;
  onSave?: (key: PreferenceKey, value: Record<string, any>) => Promise<void>;
  onDelete?: (key: PreferenceKey) => Promise<void>;
  onRefresh?: () => void;
}

export const PreferencesForm: React.FC<PreferencesFormProps> = ({
  preferences = [],
  loading = false,
  error = null,
  onSave,
  onDelete,
  onRefresh,
}) => {
  const [selectedKey, setSelectedKey] = useState<PreferenceKey>("theme");
  const [valueInput, setValueInput] = useState("");
  const [saving, setSaving] = useState(false);
  const [deleting, setDeleting] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  // Find current preference for selected key
  const currentPreference = preferences.find(
    (p) => p.preference_key === selectedKey,
  );

  useEffect(() => {
    if (currentPreference) {
      setValueInput(
        JSON.stringify(currentPreference.preference_value, null, 2),
      );
    } else {
      // Set default values based on key
      const defaults: Record<PreferenceKey, Record<string, any>> = {
        theme: { mode: "light", accent_color: "blue" },
        dashboard_layout: { widgets: [], columns: 3 },
        favorite_tables: { tables: [] },
      };
      setValueInput(JSON.stringify(defaults[selectedKey], null, 2));
    }
  }, [selectedKey, currentPreference]);

  const handleSave = async () => {
    if (!onSave) return;

    try {
      setSaving(true);
      setSuccessMessage(null);

      // Parse and validate JSON
      const parsedValue = JSON.parse(valueInput);

      await onSave(selectedKey, parsedValue);
      setSuccessMessage(`Preference "${selectedKey}" saved successfully!`);

      // T081: Track successful form submission
      usageTracker.track({
        event_type: 'form_submit',
        page_name: '/preferences',
        element_id: `preference-form-${selectedKey}`,
        success: true,
        metadata: {
          preference_key: selectedKey
        }
      });

      // Clear success message after 3 seconds
      setTimeout(() => setSuccessMessage(null), 3000);

      if (onRefresh) onRefresh();
    } catch (err) {
      // Error will be handled by parent component
      console.error("Failed to save preference:", err);
      
      // T081: Track failed form submission
      usageTracker.track({
        event_type: 'form_submit',
        page_name: '/preferences',
        element_id: `preference-form-${selectedKey}`,
        success: false,
        metadata: {
          preference_key: selectedKey,
          error: err instanceof Error ? err.message : 'Unknown error'
        }
      });
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (key: PreferenceKey) => {
    if (!onDelete) return;

    try {
      setDeleting(key);
      await onDelete(key);
      setSuccessMessage(`Preference "${key}" deleted successfully!`);

      // Clear success message after 3 seconds
      setTimeout(() => setSuccessMessage(null), 3000);

      if (onRefresh) onRefresh();
    } catch (err) {
      // Error will be handled by parent component
      console.error("Failed to delete preference:", err);
    } finally {
      setDeleting(null);
    }
  };

  const handleKeyChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    setSelectedKey(e.target.value as PreferenceKey);
  };

  // Loading state
  if (loading) {
    return (
      <div className="preferences-form-container space-y-4">
        <Skeleton className="h-12 w-full" />
        <Skeleton className="h-64 w-full" />
        <Skeleton className="h-12 w-full" />
      </div>
    );
  }

  return (
    <div
      className="preferences-form-container"
      style={{ maxWidth: "800px", margin: "0 auto" }}
    >
      {/* Header */}
      <div style={{ marginBottom: "24px" }}>
        <Typography.Title level={2} withoutMargins style={{ marginBottom: "8px" }}>
          User Preferences
        </Typography.Title>
        <Typography.Text color="secondary">
          Manage your application preferences stored in Lakebase
        </Typography.Text>
      </div>

      {/* Success Message */}
      {successMessage && (
        <Alert severity="success" className="mb-4">
          {successMessage}
        </Alert>
      )}

      {/* Error Message */}
      {error && (
        <Alert severity="error" className="mb-4">
          {error}
        </Alert>
      )}

      {/* Preference Key Selector */}
      <div style={{ marginBottom: "24px" }}>
        <Typography.Text bold style={{ display: "block", marginBottom: "8px" }}>
          Preference Key
        </Typography.Text>
        <select
          id="preference-key"
          value={selectedKey}
          onChange={handleKeyChange}
          style={{
            width: "100%",
            padding: "10px 12px",
            fontSize: "14px",
            borderRadius: "4px",
            border: "1px solid #ddd",
            backgroundColor: "#fff",
          }}
        >
          <option value="theme">Theme</option>
          <option value="dashboard_layout">Dashboard Layout</option>
          <option value="favorite_tables">Favorite Tables</option>
        </select>
      </div>

      {/* Preference Value Editor */}
      <div style={{ marginBottom: "24px" }}>
        <Typography.Text bold style={{ display: "block", marginBottom: "8px" }}>
          Preference Value (JSON)
        </Typography.Text>
        <textarea
          id="preference-value"
          value={valueInput}
          onChange={(e) => setValueInput(e.target.value)}
          rows={10}
          style={{
            width: "100%",
            padding: "12px",
            fontSize: "14px",
            fontFamily: "monospace",
            borderRadius: "4px",
            border: "1px solid #ddd",
            backgroundColor: "#fafafa",
          }}
          placeholder='{"key": "value"}'
        />
        <Typography.Hint style={{ marginTop: "4px" }}>
          Enter a valid JSON object. Max size: 100KB
        </Typography.Hint>
      </div>

      {/* Action Buttons */}
      <div style={{ display: "flex", gap: "12px", marginBottom: "24px" }}>
        <Button 
          variant="primary"
          onClick={handleSave} 
          disabled={saving}
          loading={saving}
        >
          {currentPreference ? "Update" : "Create"}
        </Button>

        {currentPreference && (
          <Button
            variant="danger"
            onClick={() => handleDelete(selectedKey)}
            disabled={deleting === selectedKey}
            loading={deleting === selectedKey}
          >
            Delete
          </Button>
        )}

        {onRefresh && (
          <Button variant="primary" onClick={onRefresh}>
            Refresh
          </Button>
        )}
      </div>

      {/* Current Preferences List */}
      <div>
        <Typography.Title level={3} withoutMargins style={{ marginBottom: "12px" }}>
          Current Preferences
        </Typography.Title>
        {preferences.length === 0 ? (
          <Alert severity="info">
            No preferences found. Create your first preference above.
          </Alert>
        ) : (
          <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
            {preferences.map((pref) => (
              <div
                key={pref.id}
                style={{
                  padding: "12px",
                  backgroundColor: "#f9f9f9",
                  borderRadius: "4px",
                  border: "1px solid #eee",
                }}
              >
                <div
                  style={{
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "start",
                  }}
                >
                  <div style={{ flex: 1 }}>
                    <Typography.Text bold style={{ marginBottom: "4px" }}>
                      {pref.preference_key}
                    </Typography.Text>
                    <Typography.Hint style={{ marginBottom: "8px" }}>
                      Updated: {new Date(pref.updated_at).toLocaleString()}
                    </Typography.Hint>
                    <pre
                      style={{
                        margin: 0,
                        padding: "8px",
                        backgroundColor: "#fff",
                        border: "1px solid #ddd",
                        borderRadius: "4px",
                        fontSize: "12px",
                        overflowX: "auto",
                      }}
                    >
                      {JSON.stringify(pref.preference_value, null, 2)}
                    </pre>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

export default PreferencesForm;
