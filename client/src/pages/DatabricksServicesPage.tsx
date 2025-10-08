/**
 * DatabricksServicesPage Component
 *
 * Main application page with tabbed interface for:
 * - Unity Catalog (query tables)
 * - Preferences (manage user preferences in Lakebase)
 * - Model Serving (invoke ML models)
 */

import React, { useState } from "react";
import { TopBar, Sidebar, Card, Button, Alert, Typography, Select, type SidebarItem } from "designbricks";
import { Database, Settings, Brain, Home } from "lucide-react";
import { DataTable } from "@/components/ui/DataTable";
import { PreferencesForm } from "@/components/ui/PreferencesForm";
import { ModelInvokeForm } from "@/components/ui/ModelInvokeForm";
import { WelcomePage } from "./WelcomePage";
import {
  UnityCatalogService,
  LakebaseService,
  ModelServingService,
  UserService,
  type UserInfo,
  type PreferenceKey,
} from "@/fastapi_client";

export function DatabricksServicesPage() {
  const [userInfo, setUserInfo] = React.useState<UserInfo | null>(null);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [activeTab, setActiveTab] = useState("welcome");

  // Unity Catalog state
  const [catalogs, setCatalogs] = useState<string[]>([]);
  const [schemas, setSchemas] = useState<string[]>([]);
  const [tables, setTables] = useState<string[]>([]);
  const [catalog, setCatalog] = useState("");
  const [schema, setSchema] = useState("");
  const [table, setTable] = useState("");
  const [catalogsLoading, setCatalogsLoading] = useState(false);
  const [schemasLoading, setSchemasLoading] = useState(false);
  const [tablesLoading, setTablesLoading] = useState(false);
  const [ucData, setUcData] = useState<any>(null);
  const [ucLoading, setUcLoading] = useState(false);
  const [ucError, setUcError] = useState<string | null>(null);

  // Preferences state
  const [preferences, setPreferences] = useState<any[]>([]);
  const [prefsLoading, setPrefsLoading] = useState(false);
  const [prefsError, setPrefsError] = useState<string | null>(null);

  // Model Serving state
  const [endpoints, setEndpoints] = useState<any[]>([]);
  const [endpointsLoading, setEndpointsLoading] = useState(false);
  const [endpointsError, setEndpointsError] = useState<string | null>(null);

  // Load user info on mount
  React.useEffect(() => {
    loadUserInfo();
    loadPreferences();
    loadEndpoints();
    loadCatalogs();
  }, []);

  // Load catalogs on mount
  const loadCatalogs = async () => {
    try {
      setCatalogsLoading(true);
      const data = await UnityCatalogService.listCatalogsApiUnityCatalogCatalogsGet();
      setCatalogs(data);
    } catch (err: any) {
      console.error("Failed to load catalogs:", err);
      setUcError(err.message || "Failed to load catalogs");
    } finally {
      setCatalogsLoading(false);
    }
  };

  // Load schemas when catalog changes
  React.useEffect(() => {
    if (catalog) {
      loadSchemas(catalog);
    } else {
      setSchemas([]);
      setSchema("");
      setTables([]);
      setTable("");
    }
  }, [catalog]);

  const loadSchemas = async (catalogName: string) => {
    try {
      setSchemasLoading(true);
      setUcError(null);
      const data = await UnityCatalogService.listSchemasApiUnityCatalogSchemasGet(catalogName);
      setSchemas(data);
      setSchema(""); // Reset schema selection
      setTables([]); // Reset tables
      setTable(""); // Reset table selection
    } catch (err: any) {
      console.error("Failed to load schemas:", err);
      setUcError(err.message || "Failed to load schemas");
      setSchemas([]);
    } finally {
      setSchemasLoading(false);
    }
  };

  // Load tables when schema changes
  React.useEffect(() => {
    if (catalog && schema) {
      loadTables(catalog, schema);
    } else {
      setTables([]);
      setTable("");
    }
  }, [catalog, schema]);

  const loadTables = async (catalogName: string, schemaName: string) => {
    try {
      setTablesLoading(true);
      setUcError(null);
      const data = await UnityCatalogService.listTableNamesApiUnityCatalogTableNamesGet(
        catalogName,
        schemaName
      );
      setTables(data);
      setTable(""); // Reset table selection
    } catch (err: any) {
      console.error("Failed to load tables:", err);
      setUcError(err.message || "Failed to load tables");
      setTables([]);
    } finally {
      setTablesLoading(false);
    }
  };

  const loadUserInfo = async () => {
    try {
      const data = await UserService.getCurrentUserApiUserMeGet();
      setUserInfo(data);
    } catch (err: any) {
      console.error("Failed to load user info:", err);
    }
  };

  // Unity Catalog functions
  const handleQueryTable = async () => {
    try {
      setUcLoading(true);
      setUcError(null);

      const result =
        await UnityCatalogService.queryTablePostApiUnityCatalogQueryPost({
          catalog,
          schema,
          table,
          limit: 100,
          offset: 0,
        });

      setUcData(result);
    } catch (err: any) {
      setUcError(err.message || "Failed to query table");
      console.error("Failed to query table:", err);
    } finally {
      setUcLoading(false);
    }
  };

  const handlePageChange = async (limit: number, offset: number) => {
    try {
      setUcLoading(true);
      setUcError(null);

      const result =
        await UnityCatalogService.queryTablePostApiUnityCatalogQueryPost({
          catalog,
          schema,
          table,
          limit,
          offset,
        });

      setUcData(result);
    } catch (err: any) {
      setUcError(err.message || "Failed to query table");
      console.error("Failed to query table:", err);
    } finally {
      setUcLoading(false);
    }
  };

  // Preferences functions
  const loadPreferences = async () => {
    try {
      setPrefsLoading(true);
      setPrefsError(null);

      const data = await LakebaseService.getPreferencesApiPreferencesGet();
      setPreferences(data);
    } catch (err: any) {
      setPrefsError(err.message || "Failed to load preferences");
      console.error("Failed to load preferences:", err);
    } finally {
      setPrefsLoading(false);
    }
  };

  const handleSavePreference = async (
    key: string,
    value: Record<string, any>,
  ) => {
    try {
      await LakebaseService.savePreferenceApiPreferencesPost({
        preference_key: key as PreferenceKey,
        preference_value: value,
      });
      await loadPreferences();
    } catch (err: any) {
      throw new Error(err.message || "Failed to save preference");
    }
  };

  const handleDeletePreference = async (key: string) => {
    try {
      await LakebaseService.deletePreferenceApiPreferencesPreferenceKeyDelete(
        key as PreferenceKey,
      );
      await loadPreferences();
    } catch (err: any) {
      throw new Error(err.message || "Failed to delete preference");
    }
  };

  // Model Serving functions
  const loadEndpoints = async () => {
    try {
      setEndpointsLoading(true);
      setEndpointsError(null);

      const data =
        await ModelServingService.listEndpointsApiModelServingEndpointsGet();
      setEndpoints(data);
    } catch (err: any) {
      setEndpointsError(err.message || "Failed to load endpoints");
      console.error("Failed to load endpoints:", err);
    } finally {
      setEndpointsLoading(false);
    }
  };

  const handleInvokeModel = async (
    endpointName: string,
    inputs: Record<string, any>,
    timeout: number,
  ) => {
    const result = await ModelServingService.invokeModelApiModelServingInvokePost(
      {
        endpoint_name: endpointName,
        inputs,
        timeout_seconds: timeout,
      },
    );
    return result;
  };

  // Sidebar configuration
  const sidebarItems: SidebarItem[] = [
    {
      id: "welcome",
      label: "Welcome",
      icon: <Home className="h-4 w-4" />,
      onClick: () => setActiveTab("welcome"),
    },
    {
      id: "unity-catalog",
      label: "Unity Catalog",
      icon: <Database className="h-4 w-4" />,
      onClick: () => setActiveTab("unity-catalog"),
    },
    {
      id: "model-serving",
      label: "Model Serving",
      icon: <Brain className="h-4 w-4" />,
      onClick: () => setActiveTab("model-serving"),
    },
    {
      id: "preferences",
      label: "Preferences",
      icon: <Settings className="h-4 w-4" />,
      onClick: () => setActiveTab("preferences"),
    },
  ];

  return (
    <div className="h-full bg-background flex flex-col" data-theme="light">
      {/* TopBar from DesignBricks */}
      <TopBar
        height={64}
        notificationCount={0}
        onMenuClick={() => setSidebarCollapsed(!sidebarCollapsed)}
        onNotificationClick={() => console.log("Notification clicked")}
        onSearchChange={(value: string) => {
          console.log("Search changed:", value);
          // TODO: Implement search functionality
        }}
        onSearchSubmit={(value: string) => {
          console.log("Search submitted:", value);
          // TODO: Implement search functionality
        }}
        searchPlaceholder="Search data, notebooks, recents, and more..."
        showMenuButton
        user={
          userInfo
            ? {
                email: userInfo.userName || "",
                name: userInfo.displayName || userInfo.userName || "",
                onClick: () => console.log("User profile clicked"),
              }
            : undefined
        }
        variant="light"
      />

      <div className="flex flex-1 overflow-hidden">
        {/* Sidebar from DesignBricks */}
        <Sidebar
          items={sidebarItems}
          activeItem={activeTab}
          collapsed={sidebarCollapsed}
          variant="light"
          width={240}
        />

        {/* Main Content Area */}
        <div className="flex-1 overflow-auto">
          <div className="container mx-auto px-4 py-8">
            {/* Welcome Section */}
            {activeTab === "welcome" && <WelcomePage embedded />}

            {/* Unity Catalog Section */}
            {activeTab === "unity-catalog" && (
              <Card padding="medium">
                <div className="flex flex-col space-y-1.5">
                  <Typography.Title level={2} withoutMargins>Query Unity Catalog Tables</Typography.Title>
                  <Typography.Text color="secondary">
                    Select a catalog, schema, and table to query data with
                    pagination
                  </Typography.Text>
                </div>
                <div className="pt-4">
                  <div className="space-y-4">
                    {/* Query Form */}
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                      <div>
                        <Select
                          label="Catalog"
                          value={catalog}
                          onChange={(value) => setCatalog(value as string)}
                          options={catalogs.map((cat) => ({ value: cat, label: cat }))}
                          placeholder="Select a catalog"
                          fullWidth
                          disabled={catalogsLoading}
                          searchable
                          clearable
                        />
                      </div>
                      <div>
                        <Select
                          label="Schema"
                          value={schema}
                          onChange={(value) => setSchema(value as string)}
                          options={schemas.map((sch) => ({ value: sch, label: sch }))}
                          placeholder="Select a schema"
                          fullWidth
                          disabled={!catalog || schemasLoading}
                          searchable
                          clearable
                        />
                      </div>
                      <div>
                        <Select
                          label="Table"
                          value={table}
                          onChange={(value) => setTable(value as string)}
                          options={tables.map((tbl) => ({ value: tbl, label: tbl }))}
                          placeholder="Select a table"
                          fullWidth
                          disabled={!catalog || !schema || tablesLoading}
                          searchable
                          clearable
                        />
                      </div>
                    </div>

                    <Button 
                      variant="primary"
                      onClick={handleQueryTable} 
                      disabled={ucLoading || !catalog || !schema || !table}
                      loading={ucLoading}
                    >
                      {ucLoading ? "Querying..." : "Query Table"}
                    </Button>

                    {/* Results */}
                    {ucError && (
                      <Alert severity="error">
                        {ucError}
                      </Alert>
                    )}

                    {ucData && (
                      <DataTable
                        catalog={catalog}
                        schema={schema}
                        table={table}
                        columns={ucData.data_source?.columns || []}
                        data={ucData.rows || []}
                        totalRows={ucData.total_row_count || ucData.row_count || 0}
                        loading={ucLoading}
                        error={ucError}
                        onPageChange={handlePageChange}
                      />
                    )}
                  </div>
                </div>
              </Card>
            )}

            {/* Model Serving Section */}
            {activeTab === "model-serving" && (
              <Card padding="medium">
                <div className="flex flex-col space-y-1.5">
                  <Typography.Title level={2} withoutMargins>Model Serving</Typography.Title>
                  <Typography.Text color="secondary">
                    Invoke ML models deployed to Databricks Model Serving
                    endpoints
                  </Typography.Text>
                </div>
                <div className="pt-4">
                  <ModelInvokeForm
                    endpoints={endpoints}
                    loading={endpointsLoading}
                    error={endpointsError}
                    onInvoke={handleInvokeModel}
                    onRefreshEndpoints={loadEndpoints}
                  />
                </div>
              </Card>
            )}

            {/* Preferences Section */}
            {activeTab === "preferences" && (
              <Card padding="medium">
                <div className="flex flex-col space-y-1.5">
                  <Typography.Title level={2} withoutMargins>User Preferences</Typography.Title>
                  <Typography.Text color="secondary">
                    Manage your preferences stored in Lakebase
                  </Typography.Text>
                </div>
                <div className="pt-4">
                  <PreferencesForm
                    preferences={preferences}
                    loading={prefsLoading}
                    error={prefsError}
                    onSave={handleSavePreference}
                    onDelete={handleDeletePreference}
                    onRefresh={loadPreferences}
                  />
                </div>
              </Card>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

export default DatabricksServicesPage;
