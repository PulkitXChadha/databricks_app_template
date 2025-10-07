/**
 * PreferencesForm Component
 *
 * CRUD form for user preferences stored in Lakebase.
 */

import React, { useState, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { Alert, AlertDescription } from "@/components/ui/alert";

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

      // Clear success message after 3 seconds
      setTimeout(() => setSuccessMessage(null), 3000);

      if (onRefresh) onRefresh();
    } catch (err) {
      // Error will be handled by parent component
      console.error("Failed to save preference:", err);
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
        <h2 style={{ margin: "0 0 8px 0" }}>User Preferences</h2>
        <p style={{ margin: 0, fontSize: "14px", color: "#666" }}>
          Manage your application preferences stored in Lakebase
        </p>
      </div>

      {/* Success Message */}
      {successMessage && (
        <Alert className="mb-4">
          <AlertDescription>{successMessage}</AlertDescription>
        </Alert>
      )}

      {/* Error Message */}
      {error && (
        <Alert variant="destructive" className="mb-4">
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      {/* Preference Key Selector */}
      <div style={{ marginBottom: "24px" }}>
        <label
          htmlFor="preference-key"
          style={{ display: "block", marginBottom: "8px", fontWeight: 600 }}
        >
          Preference Key
        </label>
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
        <label
          htmlFor="preference-value"
          style={{ display: "block", marginBottom: "8px", fontWeight: 600 }}
        >
          Preference Value (JSON)
        </label>
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
        <p style={{ marginTop: "4px", fontSize: "12px", color: "#666" }}>
          Enter a valid JSON object. Max size: 100KB
        </p>
      </div>

      {/* Action Buttons */}
      <div style={{ display: "flex", gap: "12px", marginBottom: "24px" }}>
        <Button onClick={handleSave} disabled={saving}>
          {saving ? "Saving..." : currentPreference ? "Update" : "Create"}
        </Button>

        {currentPreference && (
          <Button
            variant="destructive"
            onClick={() => handleDelete(selectedKey)}
            disabled={deleting === selectedKey}
          >
            {deleting === selectedKey ? "Deleting..." : "Delete"}
          </Button>
        )}

        {onRefresh && (
          <Button variant="outline" onClick={onRefresh}>
            Refresh
          </Button>
        )}
      </div>

      {/* Current Preferences List */}
      <div>
        <h3 style={{ margin: "0 0 12px 0", fontSize: "16px" }}>
          Current Preferences
        </h3>
        {preferences.length === 0 ? (
          <Alert>
            <AlertDescription>
              No preferences found. Create your first preference above.
            </AlertDescription>
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
                    <div style={{ fontWeight: 600, marginBottom: "4px" }}>
                      {pref.preference_key}
                    </div>
                    <div
                      style={{
                        fontSize: "12px",
                        color: "#666",
                        marginBottom: "8px",
                      }}
                    >
                      Updated: {new Date(pref.updated_at).toLocaleString()}
                    </div>
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
