import { useQuery } from "@tanstack/react-query";
import { Card, Button, Badge, Typography } from "designbricks";
import {
  Code,
  ExternalLink,
  FileText,
  Play,
  Wrench,
  User,
  Bot,
} from "lucide-react";

interface UserInfo {
  userName: string;
  displayName: string;
  active?: boolean;
  emails?: string[];
}

async function fetchUserInfo(): Promise<UserInfo> {
  const response = await fetch("/api/user/me");
  if (!response.ok) {
    throw new Error("Failed to fetch user info");
  }
  return response.json();
}

interface WelcomePageProps {
  embedded?: boolean;
}

export function WelcomePage({ embedded = false }: WelcomePageProps) {
  const { data: userInfo } = useQuery({
    queryKey: ["userInfo"],
    queryFn: fetchUserInfo,
    retry: false,
  });

  return (
    <div className={embedded ? "" : "min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 dark:from-gray-900 dark:to-gray-800"}>
      <div className="container mx-auto px-4 py-12">
        {/* Header */}
        <div className="text-center mb-12">
          <div className="flex justify-center items-center gap-3 mb-4">
            <Typography.Title level={1}>
              Welcome to your Databricks Full Stack App
            </Typography.Title>
          </div>
          <Typography.Paragraph style={{ fontSize: "1.25rem", maxWidth: "768px", margin: "0 auto" }} color="secondary">
            A modern, full-stack application template with Python FastAPI
            backend and React TypeScript frontend (using <Typography.Link href="https://pulkitxchadha.github.io/DesignBricks/?path=/docs/designbricks-introduction--docs" openInNewTab style={{ textDecoration: "underline" }}>DesignBricks Design System Components</Typography.Link>)
          </Typography.Paragraph>
        </div>

        {/* User Info Card */}
        {userInfo && (
          <Card className="mb-8 border-blue-200 bg-blue-50/50 dark:border-blue-800 dark:bg-blue-950/50" padding="medium">
            <div className="flex flex-col space-y-1.5">
              <Typography.Title level={2} withoutMargins style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                <User className="h-5 w-5" />
                Current User
              </Typography.Title>
            </div>
            <div className="pt-4">
              <div className="flex items-center gap-4">
                <div>
                  <Typography.Text bold>
                    {userInfo.displayName || userInfo.userName}
                  </Typography.Text>
                  <Typography.Text size="sm" color="secondary">
                    ({userInfo.userName})
                  </Typography.Text>
                </div>
                <Badge variant={userInfo.active ? "success" : "warning"}>
                  {userInfo.active ? "Active" : "Inactive"}
                </Badge>
              </div>
            </div>
          </Card>
        )}

        {/* Main Content Grid - First Row */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 mb-8">
          {/* Getting Started */}
          <Card className="h-fit" padding="medium">
            <div className="flex flex-col space-y-1.5">
              <Typography.Title level={2} withoutMargins style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                <Play className="h-5 w-5" />
                Getting Started
              </Typography.Title>
              <Typography.Text size="sm" color="secondary">
                Everything you need to know to start developing
              </Typography.Text>
            </div>
            <div className="space-y-4 pt-4">
              <div>
                <Typography.Text bold style={{ marginBottom: "8px" }}>Development Commands</Typography.Text>
                <div className="space-y-2">
                  <div className="flex justify-between items-center">
                    <Typography.Text code size="sm">./setup.sh</Typography.Text>
                    <Typography.Text size="sm" color="secondary">
                      Setup environment & dependencies
                    </Typography.Text>
                  </div>
                  <div className="flex justify-between items-center">
                    <Typography.Text code size="sm">./watch.sh</Typography.Text>
                    <Typography.Text size="sm" color="secondary">
                      Start dev servers (background)
                    </Typography.Text>
                  </div>
                  <div className="flex justify-between items-center">
                    <Typography.Text code size="sm">./fix.sh</Typography.Text>
                    <Typography.Text size="sm" color="secondary">
                      Format code (Python + TS)
                    </Typography.Text>
                  </div>
                  <div className="flex justify-between items-center">
                    <Typography.Text code size="sm">./deploy.sh</Typography.Text>
                    <Typography.Text size="sm" color="secondary">
                      Deploy to Databricks Apps
                    </Typography.Text>
                  </div>
                </div>
              </div>

              <div>
                <Typography.Text bold style={{ marginBottom: "8px" }}>Development Ports</Typography.Text>
                <div className="space-y-2">
                  <div className="flex justify-between items-center">
                    <Typography.Text size="sm">Frontend (React + Vite)</Typography.Text>
                    <Badge variant="info">:5173</Badge>
                  </div>
                  <div className="flex justify-between items-center">
                    <Typography.Text size="sm">Backend (FastAPI)</Typography.Text>
                    <Badge variant="info">:8000</Badge>
                  </div>
                </div>
              </div>

              <Button
                variant="primary"
                fullWidth
                iconBefore={<ExternalLink className="h-4 w-4" />}
                onClick={() => window.open("http://localhost:8000/docs", "_blank")}
              >
                Explore API Documentation
              </Button>
            </div>
          </Card>

          {/* Claude Commands */}
          <Card className="h-fit" padding="medium">
            <div className="flex flex-col space-y-1.5">
              <Typography.Title level={2} withoutMargins style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                <Bot className="h-5 w-5" />
                Claude Commands
              </Typography.Title>
              <Typography.Text size="sm" color="secondary">
                Natural language commands for development workflow
              </Typography.Text>
            </div>
            <div className="space-y-4 pt-4">
              <div>
                <Typography.Text bold style={{ marginBottom: "8px" }}>Development</Typography.Text>
                <div className="space-y-2">
                  <div className="flex justify-between items-center">
                    <Typography.Text code size="sm">
                      "start the devserver"
                    </Typography.Text>
                    <Typography.Text size="sm" color="secondary">
                      Runs ./watch.sh
                    </Typography.Text>
                  </div>
                  <div className="flex justify-between items-center">
                    <Typography.Text code size="sm">
                      "kill the devserver"
                    </Typography.Text>
                    <Typography.Text size="sm" color="secondary">
                      Stops background processes
                    </Typography.Text>
                  </div>
                  <div className="flex justify-between items-center">
                    <Typography.Text code size="sm">
                      "fix the code"
                    </Typography.Text>
                    <Typography.Text size="sm" color="secondary">Runs ./fix.sh</Typography.Text>
                  </div>
                  <div className="flex justify-between items-center">
                    <Typography.Text code size="sm">
                      "deploy the app"
                    </Typography.Text>
                    <Typography.Text size="sm" color="secondary">
                      Runs ./deploy.sh
                    </Typography.Text>
                  </div>
                </div>
              </div>

              <div>
                <Typography.Text bold style={{ marginBottom: "8px" }}>Development Tasks</Typography.Text>
                <div className="space-y-2">
                  <div className="flex justify-between items-center">
                    <Typography.Text code size="sm">
                      "add a new API endpoint"
                    </Typography.Text>
                    <Typography.Text size="sm" color="secondary">
                      Creates FastAPI routes
                    </Typography.Text>
                  </div>
                  <div className="flex justify-between items-center">
                    <Typography.Text code size="sm">
                      "create a new React component"
                    </Typography.Text>
                    <Typography.Text size="sm" color="secondary">
                      Builds UI components
                    </Typography.Text>
                  </div>
                  <div className="flex justify-between items-center">
                    <Typography.Text code size="sm">
                      "debug this error"
                    </Typography.Text>
                    <Typography.Text size="sm" color="secondary">
                      Analyzes and fixes issues
                    </Typography.Text>
                  </div>
                  <div className="flex justify-between items-center">
                    <Typography.Text code size="sm">
                      "open the UI in playwright"
                    </Typography.Text>
                    <Typography.Text size="sm" color="secondary">
                      Opens app in browser
                    </Typography.Text>
                  </div>
                </div>
              </div>
            </div>
          </Card>
        </div>

        {/* Second Row */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 mb-12">
          {/* Tech Stack */}
          <Card className="h-fit" padding="medium">
            <div className="flex flex-col space-y-1.5">
              <Typography.Title level={2} withoutMargins style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                <Code className="h-5 w-5" />
                Tech Stack
              </Typography.Title>
              <Typography.Text size="sm" color="secondary">
                Modern tools and frameworks for rapid development
              </Typography.Text>
            </div>
            <div className="pt-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                <Typography.Text bold style={{ marginBottom: "12px" }}>Backend</Typography.Text>
                  <ul className="space-y-2">
                    <li className="flex items-center gap-2">
                      <Badge variant="info" size="small">
                        Python
                      </Badge>
                      <Typography.Text size="sm">FastAPI + uvicorn</Typography.Text>
                    </li>
                    <li className="flex items-center gap-2">
                      <Badge variant="info" size="small">
                        Package
                      </Badge>
                      <Typography.Text size="sm">uv for dependencies</Typography.Text>
                    </li>
                    <li className="flex items-center gap-2">
                      <Badge variant="info" size="small">
                        SDK
                      </Badge>
                      <Typography.Text size="sm">Databricks SDK</Typography.Text>
                    </li>
                    <li className="flex items-center gap-2">
                      <Badge variant="info" size="small">
                        Quality
                      </Badge>
                      <Typography.Text size="sm">ruff for linting</Typography.Text>
                    </li>
                  </ul>
                </div>
                <div>
                  <Typography.Text bold style={{ marginBottom: "12px" }}>
                    Frontend
                  </Typography.Text>
                  <ul className="space-y-2">
                    <li className="flex items-center gap-2">
                      <Badge variant="info" size="small">
                        React
                      </Badge>
                      <Typography.Text size="sm">TypeScript + Vite</Typography.Text>
                    </li>
                    <li className="flex items-center gap-2">
                      <Badge variant="info" size="small">
                        UI
                      </Badge>
                      <Typography.Text size="sm">DesignBricks + Tailwind</Typography.Text>
                    </li>
                    <li className="flex items-center gap-2">
                      <Badge variant="info" size="small">
                        Data
                      </Badge>
                      <Typography.Text size="sm">React Query</Typography.Text>
                    </li>
                    <li className="flex items-center gap-2">
                      <Badge variant="info" size="small">
                        Package
                      </Badge>
                      <Typography.Text size="sm">bun for speed</Typography.Text>
                    </li>
                  </ul>
                </div>
              </div>
            </div>
          </Card>

          {/* Project Structure */}
          <Card className="h-fit" padding="medium">
            <div className="flex flex-col space-y-1.5">
              <Typography.Title level={2} withoutMargins style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                <FileText className="h-5 w-5" />
                Project Structure
              </Typography.Title>
              <Typography.Text size="sm" color="secondary">
                Understanding the codebase layout and key files
              </Typography.Text>
            </div>
            <div className="pt-4">
              <div className="bg-gray-50 dark:bg-gray-900/50 rounded-lg p-4 font-mono text-sm overflow-x-auto">
                <pre className="text-muted-foreground leading-relaxed">
                  {`├── server/                    # FastAPI backend
│   ├── app.py                 # Main application
│   ├── routers/               # API route handlers
│   │   ├── user.py           # User endpoints
│   │   └── insights.py       # Insights endpoints
│   └── models.py             # Data models
│
├── client/                    # React frontend
│   ├── src/
│   │   ├── pages/            # React pages
│   │   ├── components/       # UI components
│   │   ├── lib/             # Utilities
│   │   └── client/          # Generated API client
│   ├── package.json         # Frontend dependencies
│   └── vite.config.ts       # Vite configuration
│
├── scripts/                   # Development automation
│   ├── setup.sh             # Environment setup
│   ├── watch.sh             # Development server
│   ├── fix.sh               # Code formatting
│   └── deploy.sh            # Deployment
│
├── pyproject.toml            # Python dependencies
├── app.yaml                  # Databricks Apps config
└── CLAUDE.md                 # Development guide`}
                </pre>
              </div>
            </div>
          </Card>
        </div>

        {/* Features */}
        <Card className="mb-8" padding="medium">
          <div className="flex flex-col space-y-1.5">
            <Typography.Title level={2} withoutMargins style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "8px" }}>
              <Wrench className="h-5 w-5" />
              Key Features
            </Typography.Title>
            <Typography.Text size="sm" color="secondary">
              Built-in capabilities to accelerate your development
            </Typography.Text>
          </div>
          <div className="pt-4">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div className="space-y-4">
                <div className="flex items-start gap-3">
                  <Badge variant="primary" className="mt-1">Auto</Badge>
                  <div>
                    <Typography.Text bold>
                      TypeScript Client Generation </Typography.Text>
                    <Typography.Text size="sm" color="secondary">
                      Automatically generates TypeScript API client from FastAPI
                      OpenAPI spec
                    </Typography.Text>
                  </div>
                </div>
                <div className="flex items-start gap-3">
                  <Badge variant="primary" className="mt-1">Hot</Badge>
                  <div>
                    <Typography.Text bold>Hot Reloading </Typography.Text>
                    <Typography.Text size="sm" color="secondary">
                      Instant updates for both Python backend and React frontend
                      changes
                    </Typography.Text>
                  </div>
                </div>
                <div className="flex items-start gap-3">
                  <Badge variant="primary" className="mt-1">Auth</Badge>
                  <div>
                    <Typography.Text bold>Databricks Authentication </Typography.Text>
                    <Typography.Text size="sm" color="secondary">
                      Integrated with Databricks SDK for seamless workspace
                      integration
                    </Typography.Text>
                  </div>
                </div>
              </div>
              <div className="space-y-4">
                <div className="flex items-start gap-3">
                  <Badge variant="primary" className="mt-1">Deploy</Badge>
                  <div>
                    <Typography.Text bold>Databricks Apps Ready </Typography.Text>
                    <Typography.Text size="sm" color="secondary">
                      Pre-configured for deployment to Databricks Apps platform
                    </Typography.Text>
                  </div>
                </div>
                <div className="flex items-start gap-3">
                  <Badge variant="primary" className="mt-1">Quality</Badge>
                  <div>
                    <Typography.Text bold>Code Quality Tools </Typography.Text>
                    <Typography.Text size="sm" color="secondary">
                      Automated formatting with ruff (Python) and prettier
                      (TypeScript)
                    </Typography.Text>
                  </div>
                </div>
                <div className="flex items-start gap-3">
                  <Badge variant="primary" className="mt-1">Logs</Badge>
                  <div>
                    <Typography.Text bold>Background Development </Typography.Text>
                    <Typography.Text size="sm" color="secondary">
                      Development servers run in background with comprehensive
                      logging
                    </Typography.Text>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </Card>

        {/* Footer */}
        <div className="text-center mt-12 pt-8 border-t">
          <Typography.Paragraph color="secondary">
            Ready to build something amazing? Check out the{" "}
            <Typography.Link
              href="http://localhost:8000/docs"
              openInNewTab
            >
              API documentation
            </Typography.Link>{" "}
            to get started with your endpoints.
          </Typography.Paragraph>
        </div>
      </div>
    </div>
  );
}
