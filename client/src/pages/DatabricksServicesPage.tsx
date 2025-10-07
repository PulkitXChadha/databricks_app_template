/**
 * DatabricksServicesPage Component
 *
 * Main application page with tabbed interface for:
 * - Unity Catalog (query tables)
 * - Preferences (manage user preferences in Lakebase)
 * - Model Serving (invoke ML models)
 */

import React, { useState } from "react";
import { TopBar, Sidebar, type SidebarItem } from "designbricks";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Database, Settings, Brain } from "lucide-react";
import { DataTable } from "@/components/ui/DataTable";
import { PreferencesForm } from "@/components/ui/PreferencesForm";
import { ModelInvokeForm } from "@/components/ui/ModelInvokeForm";
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
  const [activeTab, setActiveTab] = useState("unity-catalog");

  // Unity Catalog state
  const [catalog, setCatalog] = useState("main");
  const [schema, setSchema] = useState("samples");
  const [table, setTable] = useState("demo_data");
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
  }, []);

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
        await UnityCatalogService.queryTableApiUnityCatalogQueryPost({
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
        await UnityCatalogService.queryTableApiUnityCatalogQueryPost({
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
    <div className="min-h-screen bg-background">
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

      <div className="flex" style={{ height: "calc(100vh - 64px)" }}>
        {/* Sidebar from DesignBricks */}
        <Sidebar
          items={sidebarItems}
          activeItem={activeTab}
          collapsed={sidebarCollapsed}
          onCollapsedChange={setSidebarCollapsed}
          collapsible={true}
          variant="light"
          width={240}
        />

        {/* Main Content Area */}
        <div className="flex-1 overflow-auto">
          <div className="container mx-auto px-4 py-8">
            {/* Header */}
            <div className="mb-8">
              <h1 className="text-3xl font-bold mb-2">
                Databricks App Template
              </h1>
              <p className="text-muted-foreground">
                Integrated Unity Catalog, Lakebase, and Model Serving
              </p>
            </div>

            {/* Tabbed Interface */}
            <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
          <TabsList className="grid w-full grid-cols-3 mb-8">
            <TabsTrigger
              value="unity-catalog"
              className="flex items-center gap-2"
            >
              <Database className="h-4 w-4" />
              Unity Catalog
            </TabsTrigger>
            <TabsTrigger
              value="model-serving"
              className="flex items-center gap-2"
            >
              <Brain className="h-4 w-4" />
              Model Serving
            </TabsTrigger>
            <TabsTrigger
              value="preferences"
              className="flex items-center gap-2"
            >
              <Settings className="h-4 w-4" />
              Preferences
            </TabsTrigger>
          </TabsList>

          {/* Unity Catalog Tab */}
          <TabsContent value="unity-catalog">
            <Card>
              <CardHeader>
                <CardTitle>Query Unity Catalog Tables</CardTitle>
                <CardDescription>
                  Select a catalog, schema, and table to query data with
                  pagination
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  {/* Query Form */}
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                    <div>
                      <label
                        htmlFor="catalog"
                        className="block text-sm font-medium mb-2"
                      >
                        Catalog
                      </label>
                      <Input
                        id="catalog"
                        value={catalog}
                        onChange={(e) => setCatalog(e.target.value)}
                        placeholder="main"
                      />
                    </div>
                    <div>
                      <label
                        htmlFor="schema"
                        className="block text-sm font-medium mb-2"
                      >
                        Schema
                      </label>
                      <Input
                        id="schema"
                        value={schema}
                        onChange={(e) => setSchema(e.target.value)}
                        placeholder="samples"
                      />
                    </div>
                    <div>
                      <label
                        htmlFor="table"
                        className="block text-sm font-medium mb-2"
                      >
                        Table
                      </label>
                      <Input
                        id="table"
                        value={table}
                        onChange={(e) => setTable(e.target.value)}
                        placeholder="demo_data"
                      />
                    </div>
                  </div>

                  <Button onClick={handleQueryTable} disabled={ucLoading}>
                    {ucLoading ? "Querying..." : "Query Table"}
                  </Button>

                  {/* Results */}
                  {ucError && (
                    <Alert variant="destructive">
                      <AlertDescription>{ucError}</AlertDescription>
                    </Alert>
                  )}

                  {ucData && (
                    <DataTable
                      catalog={catalog}
                      schema={schema}
                      table={table}
                      columns={ucData.data_source?.columns || []}
                      data={ucData.rows || []}
                      totalRows={ucData.row_count || 0}
                      loading={ucLoading}
                      error={ucError}
                      onPageChange={handlePageChange}
                    />
                  )}
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          {/* Model Serving Tab */}
          <TabsContent value="model-serving">
            <Card>
              <CardHeader>
                <CardTitle>Model Serving</CardTitle>
                <CardDescription>
                  Invoke ML models deployed to Databricks Model Serving
                  endpoints
                </CardDescription>
              </CardHeader>
              <CardContent>
                <ModelInvokeForm
                  endpoints={endpoints}
                  loading={endpointsLoading}
                  error={endpointsError}
                  onInvoke={handleInvokeModel}
                  onRefreshEndpoints={loadEndpoints}
                />
              </CardContent>
            </Card>
          </TabsContent>


          {/* Preferences Tab */}
          <TabsContent value="preferences">
            <Card>
              <CardHeader>
                <CardTitle>User Preferences</CardTitle>
                <CardDescription>
                  Manage your preferences stored in Lakebase
                </CardDescription>
              </CardHeader>
              <CardContent>
                <PreferencesForm
                  preferences={preferences}
                  loading={prefsLoading}
                  error={prefsError}
                  onSave={handleSavePreference}
                  onDelete={handleDeletePreference}
                  onRefresh={loadPreferences}
                />
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>
          </div>
        </div>
      </div>
    </div>
  );
}

export default DatabricksServicesPage;
