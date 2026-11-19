"use client";

import * as React from "react";
import {
  Activity,
  AlertCircle,
  ArrowDownToLine,
  CheckCircle2,
  Clock,
  Coins,
  Cpu,
  Database,
  Download,
  KeyRound,
  Layers,
  Lock,
  LogOut,
  Play,
  RefreshCw,
  Shield,
  ShieldAlert,
  ShieldCheck,
  Sparkles,
  Timer,
} from "lucide-react";
import { format, formatDistanceToNow } from "date-fns";

import {
  AdminDashboardData,
  api,
  CollectionRunItem,
  SourceStat,
} from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { Separator } from "@/components/ui/separator";

const STORAGE_KEY = "launchboard_admin_key";

export default function AdminPage() {
  const [apiKey, setApiKey] = React.useState("");
  const [inputKey, setInputKey] = React.useState("");
  const [isAuthenticated, setIsAuthenticated] = React.useState(false);
  const [isInitializing, setIsInitializing] = React.useState(true);

  // Dashboard Data State
  const [dashboardData, setDashboardData] = React.useState<AdminDashboardData | null>(null);
  const [isLoadingData, setIsLoadingData] = React.useState(false);
  const [errorMsg, setErrorMsg] = React.useState<string | null>(null);

  // Trigger Refresh State
  const [isRefreshing, setIsRefreshing] = React.useState(false);
  const [refreshingSources, setRefreshingSources] = React.useState<Record<string, boolean>>({});
  const [refreshNotice, setRefreshNotice] = React.useState<{
    type: "success" | "error";
    text: string;
  } | null>(null);

  // Check sessionStorage on mount
  React.useEffect(() => {
    if (typeof window !== "undefined") {
      const stored = sessionStorage.getItem(STORAGE_KEY);
      if (stored) {
        setApiKey(stored);
        setIsAuthenticated(true);
      }
    }
    setIsInitializing(false);
  }, []);

  // Fetch Admin Dashboard Data
  const loadDashboard = React.useCallback(async (key: string) => {
    setIsLoadingData(true);
    setErrorMsg(null);
    try {
      const data = await api.getAdminDashboard(key);
      setDashboardData(data);
    } catch (err) {
      console.warn("Could not fetch admin dashboard from backend:", err);
      // Fallback: If backend is offline or returned an error, construct a display view
      // and notify the user while keeping the admin dashboard functional.
      setErrorMsg(
        err instanceof Error
          ? err.message
          : "Backend admin endpoint currently unreachable. Verify NEXT_PUBLIC_API_URL or API key."
      );
    } finally {
      setIsLoadingData(false);
    }
  }, []);

  React.useEffect(() => {
    if (isAuthenticated && apiKey) {
      loadDashboard(apiKey);
    }
  }, [isAuthenticated, apiKey, loadDashboard]);

  // Handle Login
  const handleLogin = (e: React.FormEvent) => {
    e.preventDefault();
    if (!inputKey.trim()) return;
    const cleanKey = inputKey.trim();
    if (typeof window !== "undefined") {
      sessionStorage.setItem(STORAGE_KEY, cleanKey);
    }
    setApiKey(cleanKey);
    setIsAuthenticated(true);
    setInputKey("");
  };

  // Handle Logout
  const handleLogout = () => {
    if (typeof window !== "undefined") {
      sessionStorage.removeItem(STORAGE_KEY);
    }
    setApiKey("");
    setIsAuthenticated(false);
    setDashboardData(null);
    setErrorMsg(null);
  };

  // Trigger Refresh
  const handleTriggerRefresh = async () => {
    if (!apiKey) return;
    setIsRefreshing(true);
    setRefreshNotice(null);
    try {
      const res = await api.triggerRefresh(apiKey);
      setRefreshNotice({
        type: "success",
        text: `Ingestion job started (Run ID: ${res.run_id.slice(0, 8)}). Data will update automatically.`,
      });
      // Re-fetch dashboard after short delay
      setTimeout(() => loadDashboard(apiKey), 2500);
    } catch (err) {
      setRefreshNotice({
        type: "error",
        text: err instanceof Error ? err.message : "Failed to trigger refresh.",
      });
    } finally {
      setIsRefreshing(false);
    }
  };

  // Refresh individual source
  const handleRefreshSource = async (sourceName: string) => {
    if (!apiKey || refreshingSources[sourceName]) return;
    setRefreshingSources((prev) => ({ ...prev, [sourceName]: true }));
    setRefreshNotice(null);
    try {
      const res = await api.triggerRefresh(apiKey, [sourceName]);
      setRefreshNotice({
        type: "success",
        text: `Targeted collection started for ${sourceName} (Run ID: ${res.run_id.slice(0, 8)}).`,
      });
      setTimeout(() => loadDashboard(apiKey), 2500);
    } catch (err) {
      setRefreshNotice({
        type: "error",
        text: err instanceof Error ? err.message : `Failed to refresh source ${sourceName}.`,
      });
    } finally {
      setRefreshingSources((prev) => ({ ...prev, [sourceName]: false }));
    }
  };

  const handleExportCsv = async () => {
  if (!apiKey) return;

  try {
    await api.exportEvaluationCsv(apiKey);
  } catch (err) {
    setErrorMsg(
      err instanceof Error ? err.message : "CSV export failed."
    );
  }
};

  const formatDate = (dateStr: string | null | undefined): string => {
    if (!dateStr) return "Never";
    try {
      const d = new Date(dateStr);
      return format(d, "MMM d, yyyy HH:mm:ss");
    } catch {
      return dateStr;
    }
  };

  const formatRelative = (dateStr: string | null | undefined): string => {
    if (!dateStr) return "";
    try {
      return formatDistanceToNow(new Date(dateStr), { addSuffix: true });
    } catch {
      return "";
    }
  };

  if (isInitializing) {
    return (
      <div className="container max-w-5xl py-20 text-center">
        <Skeleton className="h-10 w-48 mx-auto mb-4" />
        <Skeleton className="h-32 w-full max-w-md mx-auto rounded-xl" />
      </div>
    );
  }

  // Login Form if Not Authenticated
  if (!isAuthenticated) {
    return (
      <div className="container max-w-md px-4 py-20">
        <Card className="border bg-card shadow-lg">
          <CardHeader className="text-center pb-4">
            <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-primary/10 text-primary mb-3">
              <Shield className="h-6 w-6" />
            </div>
            <CardTitle className="text-2xl font-bold">Admin Portal</CardTitle>
            <CardDescription className="text-xs">
              Enter the LaunchBoard Admin API Key to access metrics, LLM reports, and trigger ingestion runs.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleLogin} className="space-y-4">
              <div className="space-y-1.5">
                <Label htmlFor="admin-key" className="text-xs font-medium">
                  Admin API Secret Key
                </Label>
                <div className="relative">
                  <KeyRound className="absolute left-3 top-2.5 h-4 w-4 text-muted-foreground" />
                  <Input
                    id="admin-key"
                    type="password"
                    placeholder="e.g. lb_secret_admin_key"
                    value={inputKey}
                    onChange={(e) => setInputKey(e.target.value)}
                    className="pl-9 text-sm"
                    required
                  />
                </div>
              </div>

              <Button type="submit" className="w-full font-medium shadow-sm">
                <Lock className="mr-2 h-4 w-4" />
                Authenticate Session
              </Button>

              <p className="text-[11px] text-center text-muted-foreground leading-relaxed pt-2">
                Key will be stored in your browser&apos;s sessionStorage and sent securely with admin requests.
              </p>
            </form>
          </CardContent>
        </Card>
      </div>
    );
  }

  // Loading state - show skeletons while data is being fetched
  if (isLoadingData && !dashboardData) {
    return (
      <div className="container max-w-7xl px-4 sm:px-8 py-10 space-y-8">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between border-b border-border/60 pb-6">
          <div>
            <div className="flex items-center space-x-2">
              <h1 className="text-3xl font-extrabold tracking-tight text-foreground">
                Admin &amp; Pipeline Operations
              </h1>
              <Badge variant="outline" className="border-emerald-500/30 text-emerald-600 bg-emerald-500/10 text-xs">
                Authenticated
              </Badge>
            </div>
            <p className="mt-1 text-sm text-muted-foreground">Loading dashboard data...</p>
          </div>
          <Button variant="ghost" size="sm" onClick={handleLogout} className="text-xs text-muted-foreground hover:text-destructive">
            <LogOut className="mr-1.5 h-3.5 w-3.5" />
            Disconnect
          </Button>
        </div>
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-6">
          {Array.from({ length: 6 }).map((_, i) => (
            <Card key={i} className="border bg-card shadow-none">
              <CardHeader className="p-4 pb-1">
                <Skeleton className="h-3 w-20" />
              </CardHeader>
              <CardContent className="p-4 pt-1">
                <Skeleton className="h-7 w-16" />
                <Skeleton className="h-2 w-24 mt-2" />
              </CardContent>
            </Card>
          ))}
        </div>
      </div>
    );
  }

  // Error state - no data and backend returned an error
  if (!dashboardData && errorMsg) {
    return (
      <div className="container max-w-5xl px-4 py-20 text-center">
        <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-destructive/10 text-destructive mb-4">
          <AlertCircle className="h-6 w-6" />
        </div>
        <h2 className="text-xl font-bold text-foreground">Unable to load Admin Dashboard</h2>
        <p className="mt-2 text-sm text-muted-foreground max-w-md mx-auto">{errorMsg}</p>
        <div className="mt-6 flex justify-center gap-3">
          <Button onClick={() => loadDashboard(apiKey)} className="shadow-sm">
            <RefreshCw className="mr-2 h-4 w-4" />
            Retry
          </Button>
          <Button variant="ghost" size="sm" onClick={handleLogout} className="text-xs text-muted-foreground hover:text-destructive">
            <LogOut className="mr-1.5 h-3.5 w-3.5" />
            Disconnect
          </Button>
        </div>
      </div>
    );
  }

  // Safe display data with defensive defaults — never use fabricated numbers
  const displayData: AdminDashboardData = dashboardData ?? {
    total_jobs_collected: 0,
    unique_jobs: 0,
    duplicate_jobs_detected: 0,
    jobs_classified: 0,
    failed_classifications: 0,
    source_stats: [],
    cost_report: {
      total_input_tokens: 0,
      total_output_tokens: 0,
      total_tokens: 0,
      total_requests: 0,
      total_cost_usd: 0,
      avg_cost_per_job: 0,
      cost_per_1000_jobs: 0,
      model_name: "N/A",
      pricing_config: {},
      last_updated: null,
      note: "No data available yet. Trigger a refresh to start collecting.",
    },
    last_collection_run: null,
    collection_history: [],
    restricted_sources: [],
    scheduler_status: null,
  };

  return (
    <div className="container max-w-7xl px-4 sm:px-8 py-10 space-y-8">
      {/* Top Header & Actions */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between border-b border-border/60 pb-6">
        <div>
          <div className="flex items-center space-x-2">
            <h1 className="text-3xl font-extrabold tracking-tight text-foreground">
              Admin & Pipeline Operations
            </h1>
            <Badge variant="outline" className="border-emerald-500/30 text-emerald-600 bg-emerald-500/10 text-xs">
              Authenticated
            </Badge>
          </div>
          <p className="mt-1 text-sm text-muted-foreground flex items-center gap-2">
            <Clock className="h-3.5 w-3.5" />
            Last Successful Run:{" "}
            <span className="font-medium text-foreground">
              {formatDate(displayData.last_collection_run?.completed_at)}
            </span>
            {displayData.last_collection_run?.completed_at && (
              <span className="text-xs text-muted-foreground">
                ({formatRelative(displayData.last_collection_run.completed_at)})
              </span>
            )}
          </p>
        </div>

        {/* Action Buttons */}
        <div className="flex flex-wrap items-center gap-2.5">
          <Button
            onClick={handleTriggerRefresh}
            disabled={isRefreshing}
            className="text-xs font-semibold shadow-sm"
          >
            <Play className={`mr-1.5 h-3.5 w-3.5 ${isRefreshing ? "animate-spin" : ""}`} />
            {isRefreshing ? "Running Refresh..." : "Trigger Refresh"}
          </Button>

          <Button
            variant="outline"
            onClick={handleExportCsv}
            className="text-xs font-medium"
          >
            <Download className="mr-1.5 h-3.5 w-3.5" />
            Export Evaluation CSV
          </Button>

          <Button
            variant="ghost"
            size="sm"
            onClick={handleLogout}
            className="text-xs text-muted-foreground hover:text-destructive"
          >
            <LogOut className="mr-1.5 h-3.5 w-3.5" />
            Disconnect
          </Button>
        </div>
      </div>

      {/* Notifications / Error Banner */}
      {refreshNotice && (
        <div
          className={`rounded-lg border p-4 text-xs font-medium flex items-center justify-between ${
            refreshNotice.type === "success"
              ? "border-emerald-500/30 bg-emerald-500/10 text-emerald-700 dark:text-emerald-300"
              : "border-destructive/30 bg-destructive/10 text-destructive"
          }`}
        >
          <div className="flex items-center space-x-2">
            {refreshNotice.type === "success" ? (
              <CheckCircle2 className="h-4 w-4 shrink-0" />
            ) : (
              <AlertCircle className="h-4 w-4 shrink-0" />
            )}
            <span>{refreshNotice.text}</span>
          </div>
          <button
            onClick={() => setRefreshNotice(null)}
            className="text-xs opacity-70 hover:opacity-100"
          >
            Dismiss
          </button>
        </div>
      )}

      {errorMsg && (
        <div className="rounded-lg border border-amber-500/30 bg-amber-500/10 p-4 text-xs text-amber-700 dark:text-amber-400 flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <AlertCircle className="h-4 w-4 shrink-0" />
            <span>Note: {errorMsg} (Displaying cached pipeline snapshot below)</span>
          </div>
          <Button
            variant="outline"
            size="sm"
            onClick={() => loadDashboard(apiKey)}
            className="h-7 text-xs border-amber-500/30"
          >
            <RefreshCw className="mr-1 h-3 w-3" />
            Sync
          </Button>
        </div>
      )}

      {/* =========================================================================
          Dashboard Cards: Total, Unique, Duplicates, Classified, Failed, Cost
         ========================================================================= */}
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-6">
        <Card className="border bg-card shadow-none">
          <CardHeader className="p-4 pb-1">
            <CardDescription className="text-xs uppercase font-medium">Total Collected</CardDescription>
          </CardHeader>
          <CardContent className="p-4 pt-1">
            <div className="text-2xl font-bold tracking-tight text-foreground">
              {displayData.total_jobs_collected.toLocaleString()}
            </div>
            <p className="text-[10px] text-muted-foreground mt-1">Raw postings fetched</p>
          </CardContent>
        </Card>

        <Card className="border bg-card shadow-none">
          <CardHeader className="p-4 pb-1">
            <CardDescription className="text-xs uppercase font-medium">Unique Jobs</CardDescription>
          </CardHeader>
          <CardContent className="p-4 pt-1">
            <div className="text-2xl font-bold tracking-tight text-primary">
              {displayData.unique_jobs.toLocaleString()}
            </div>
            <p className="text-[10px] text-muted-foreground mt-1">Verified deduplicated</p>
          </CardContent>
        </Card>

        <Card className="border bg-card shadow-none">
          <CardHeader className="p-4 pb-1">
            <CardDescription className="text-xs uppercase font-medium">Duplicates</CardDescription>
          </CardHeader>
          <CardContent className="p-4 pt-1">
            <div className="text-2xl font-bold tracking-tight text-amber-600 dark:text-amber-400">
              {displayData.duplicate_jobs_detected.toLocaleString()}
            </div>
            <p className="text-[10px] text-muted-foreground mt-1">Cross-posts dropped</p>
          </CardContent>
        </Card>

        <Card className="border bg-card shadow-none">
          <CardHeader className="p-4 pb-1">
            <CardDescription className="text-xs uppercase font-medium">Jobs Classified</CardDescription>
          </CardHeader>
          <CardContent className="p-4 pt-1">
            <div className="text-2xl font-bold tracking-tight text-emerald-600 dark:text-emerald-400">
              {displayData.jobs_classified.toLocaleString()}
            </div>
            <p className="text-[10px] text-muted-foreground mt-1">AI categorization done</p>
          </CardContent>
        </Card>

        <Card className="border bg-card shadow-none">
          <CardHeader className="p-4 pb-1">
            <CardDescription className="text-xs uppercase font-medium">Failed Classify</CardDescription>
          </CardHeader>
          <CardContent className="p-4 pt-1">
            <div className="text-2xl font-bold tracking-tight text-destructive">
              {displayData.failed_classifications.toLocaleString()}
            </div>
            <p className="text-[10px] text-muted-foreground mt-1">Parse errors or malformed</p>
          </CardContent>
        </Card>

        <Card className="border bg-card shadow-none">
          <CardHeader className="p-4 pb-1">
            <CardDescription className="text-xs uppercase font-medium">LLM Total Cost</CardDescription>
          </CardHeader>
          <CardContent className="p-4 pt-1">
            <div className="text-2xl font-bold tracking-tight text-purple-600 dark:text-purple-400">
              ${displayData.cost_report.total_cost_usd.toFixed(3)}
            </div>
            <p className="text-[10px] text-muted-foreground mt-1">
              ${displayData.cost_report.cost_per_1000_jobs.toFixed(3)} / 1k jobs
            </p>
          </CardContent>
        </Card>
      </div>

      {/* =========================================================================
          LLM Cost Report Detail Card
         ========================================================================= */}
      <Card className="border bg-card shadow-sm">
        <CardHeader className="p-5 pb-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-2">
              <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-purple-500/10 text-purple-600">
                <Cpu className="h-4 w-4" />
              </div>
              <div>
                <CardTitle className="text-base font-semibold">
                  LLM Classification Cost & Token Usage Report
                </CardTitle>
                <CardDescription className="text-xs">
                  Model: <span className="font-medium text-foreground">{displayData.cost_report.model_name}</span> | {displayData.cost_report.note}
                </CardDescription>
              </div>
            </div>
            <Badge variant="outline" className="text-xs font-mono">
              Tokens: {displayData.cost_report.total_tokens.toLocaleString()}
            </Badge>
          </div>
        </CardHeader>
        <CardContent className="p-5 pt-0">
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 pt-3 border-t border-border/60 text-xs">
            <div>
              <p className="text-muted-foreground">Input Tokens</p>
              <p className="font-semibold text-foreground text-sm mt-0.5">
                {displayData.cost_report.total_input_tokens.toLocaleString()}
              </p>
            </div>
            <div>
              <p className="text-muted-foreground">Output Tokens</p>
              <p className="font-semibold text-foreground text-sm mt-0.5">
                {displayData.cost_report.total_output_tokens.toLocaleString()}
              </p>
            </div>
            <div>
              <p className="text-muted-foreground">Avg Cost / Job</p>
              <p className="font-semibold text-foreground text-sm mt-0.5">
                ${displayData.cost_report.avg_cost_per_job.toFixed(6)}
              </p>
            </div>
            <div>
              <p className="text-muted-foreground">Cost per 1,000 Jobs</p>
              <p className="font-semibold text-foreground text-sm mt-0.5">
                ${displayData.cost_report.cost_per_1000_jobs.toFixed(4)}
              </p>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* =========================================================================
          Automated Scheduler Status Card
         ========================================================================= */}
      {displayData.scheduler_status && (
        <Card className="border bg-card shadow-sm">
          <CardHeader className="p-5 pb-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-2">
                <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-blue-500/10 text-primary">
                  <Timer className="h-4 w-4" />
                </div>
                <div>
                  <CardTitle className="text-base font-semibold">
                    Autonomous Ingestion Engine (Background Scheduler)
                  </CardTitle>
                  <CardDescription className="text-xs">
                    Automated background collector daemon cycles every {displayData.scheduler_status.interval_minutes} minutes without overlapping runs.
                  </CardDescription>
                </div>
              </div>
              <Badge
                variant="outline"
                className={
                  displayData.scheduler_status.is_running
                    ? "border-emerald-500/30 text-emerald-600 bg-emerald-500/10"
                    : "border-muted text-muted-foreground bg-muted/20"
                }
              >
                <span className={`mr-1.5 h-2 w-2 rounded-full ${displayData.scheduler_status.is_running ? "bg-emerald-500 animate-pulse" : "bg-muted-foreground"}`} />
                {displayData.scheduler_status.is_running ? "Daemon Active (30m Interval)" : "Scheduler Stopped"}
              </Badge>
            </div>
          </CardHeader>
          <CardContent className="p-5 pt-0">
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 pt-3 border-t border-border/60 text-xs">
              <div>
                <p className="text-muted-foreground">Cadence Interval</p>
                <p className="font-semibold text-foreground text-sm mt-0.5">
                  Every {displayData.scheduler_status.interval_minutes} minutes
                </p>
              </div>
              <div>
                <p className="text-muted-foreground">Last Scheduled Run</p>
                <p className="font-semibold text-foreground text-sm mt-0.5">
                  {formatDate(displayData.scheduler_status.last_run_completed_at || displayData.scheduler_status.last_run_started_at)}
                </p>
              </div>
              <div>
                <p className="text-muted-foreground">Next Scheduled Run</p>
                <p className="font-semibold text-foreground text-sm mt-0.5">
                  {displayData.scheduler_status.next_run_at ? formatDate(displayData.scheduler_status.next_run_at) : "Pending"}
                </p>
              </div>
              <div>
                <p className="text-muted-foreground">Scheduled Runs Completed</p>
                <p className="font-semibold text-foreground text-sm mt-0.5">
                  {displayData.scheduler_status.total_scheduled_runs} cycles executed
                </p>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* =========================================================================
          Source-wise Stats Table
         ========================================================================= */}
      <Card className="border bg-card shadow-sm">
        <CardHeader className="p-5 pb-3">
          <CardTitle className="text-base font-semibold flex items-center gap-2">
            <Database className="h-4 w-4 text-primary" />
            Source Ingestion Statistics
          </CardTitle>
          <CardDescription className="text-xs">
            Active collectors, collection health, and deduplication yield per external source.
          </CardDescription>
        </CardHeader>
        <CardContent className="p-0">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-muted/50 text-muted-foreground uppercase tracking-wider font-semibold border-b border-border">
                <tr>
                  <th className="px-5 py-3">Source Name</th>
                  <th className="px-5 py-3">Total Collected</th>
                  <th className="px-5 py-3">Total Runs</th>
                  <th className="px-5 py-3">Status</th>
                  <th className="px-5 py-3">Failures</th>
                  <th className="px-5 py-3">Last Success</th>
                  <th className="px-5 py-3 text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {displayData.source_stats.length === 0 ? (
                  <tr>
                    <td colSpan={7} className="px-5 py-8 text-center text-sm text-muted-foreground">
                      No source data available yet. Trigger a refresh to start collecting.
                    </td>
                  </tr>
                ) : (
                  displayData.source_stats.map((s, idx) => {
                    const successRate = s.total_runs > 0
                      ? (((s.total_runs - s.total_failures) / s.total_runs) * 100)
                      : 0;
                    const sourceStatus = !s.is_enabled
                      ? "disabled"
                      : s.consecutive_failures > 2
                      ? "error"
                      : s.consecutive_failures > 0
                      ? "warning"
                      : "active";

                    return (
                      <tr key={idx} className="hover:bg-muted/30 transition-colors">
                        <td className="px-5 py-3.5 font-semibold text-foreground capitalize">
                          {s.source_name}
                        </td>
                        <td className="px-5 py-3.5 text-muted-foreground">
                          {(s.total_jobs_collected ?? 0).toLocaleString()}
                        </td>
                        <td className="px-5 py-3.5 font-medium text-foreground">
                          {(s.total_runs ?? 0).toLocaleString()}
                        </td>
                        <td className="px-5 py-3.5">
                          <Badge
                            variant="secondary"
                            className={
                              sourceStatus === "active"
                                ? "bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border-emerald-500/20"
                                : sourceStatus === "error"
                                ? "bg-destructive/10 text-destructive border-destructive/20"
                                : sourceStatus === "disabled"
                                ? "bg-muted text-muted-foreground border-border"
                                : "bg-amber-500/10 text-amber-600 dark:text-amber-400 border-amber-500/20"
                            }
                          >
                            {sourceStatus} ({successRate.toFixed(0)}%)
                          </Badge>
                        </td>
                        <td className="px-5 py-3.5 text-muted-foreground">
                          {(s.total_failures ?? 0).toLocaleString()}
                        </td>
                        <td className="px-5 py-3.5 text-muted-foreground">
                          {formatDate(s.last_success_at)}
                        </td>
                        <td className="px-5 py-3.5 text-right">
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => handleRefreshSource(s.source_name)}
                            disabled={refreshingSources[s.source_name] || isRefreshing}
                            className="h-7 px-2.5 text-xs text-muted-foreground hover:text-foreground border-border/80"
                            title={`Trigger refresh for ${s.source_name}`}
                          >
                            <RefreshCw
                              className={`h-3 w-3 mr-1 ${
                                refreshingSources[s.source_name] ? "animate-spin text-primary" : ""
                              }`}
                            />
                            {refreshingSources[s.source_name] ? "Fetching..." : "Refresh"}
                          </Button>
                        </td>
                      </tr>
                    );
                  })
                )}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>

      {/* =========================================================================
          Collection History Table (Last 10 runs)
         ========================================================================= */}
      <Card className="border bg-card shadow-sm">
        <CardHeader className="p-5 pb-3">
          <CardTitle className="text-base font-semibold flex items-center gap-2">
            <Clock className="h-4 w-4 text-primary" />
            Collection Run History (Last 10 Runs)
          </CardTitle>
          <CardDescription className="text-xs">
            Automated refresh logs with duration and conversion statistics.
          </CardDescription>
        </CardHeader>
        <CardContent className="p-0">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-muted/50 text-muted-foreground uppercase tracking-wider font-semibold border-b border-border">
                <tr>
                  <th className="px-5 py-3">Run ID</th>
                  <th className="px-5 py-3">Started At</th>
                  <th className="px-5 py-3">Duration</th>
                  <th className="px-5 py-3">Fetched</th>
                  <th className="px-5 py-3">New Jobs</th>
                  <th className="px-5 py-3">Duplicates</th>
                  <th className="px-5 py-3">Classified</th>
                  <th className="px-5 py-3">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {displayData.collection_history.length === 0 ? (
                  <tr>
                    <td colSpan={8} className="px-5 py-8 text-center text-sm text-muted-foreground">
                      No collection runs yet. Trigger a refresh to start.
                    </td>
                  </tr>
                ) : (
                  displayData.collection_history.map((run) => (
                    <tr key={run.id} className="hover:bg-muted/30 transition-colors">
                      <td className="px-5 py-3.5 font-mono font-medium text-foreground">
                        {(run.id ?? "").slice(0, 16)}
                      </td>
                      <td className="px-5 py-3.5 text-muted-foreground">
                        {formatDate(run.started_at)}
                      </td>
                      <td className="px-5 py-3.5 text-muted-foreground">
                        {run.duration_seconds != null ? `${run.duration_seconds.toFixed(1)}s` : "--"}
                      </td>
                      <td className="px-5 py-3.5 font-medium">{run.total_fetched ?? 0}</td>
                      <td className="px-5 py-3.5 font-medium text-primary">+{run.total_new ?? 0}</td>
                      <td className="px-5 py-3.5 text-amber-600 dark:text-amber-400">
                        {run.total_duplicates ?? 0}
                      </td>
                      <td className="px-5 py-3.5 font-medium text-emerald-600 dark:text-emerald-400">
                        {run.total_classified ?? 0}
                      </td>
                      <td className="px-5 py-3.5">
                        <Badge
                          variant="secondary"
                          className={
                            run.status === "completed"
                              ? "bg-emerald-500/10 text-emerald-600 dark:text-emerald-400"
                              : run.status === "running"
                              ? "bg-blue-500/10 text-blue-600 dark:text-blue-400"
                              : "bg-destructive/10 text-destructive"
                          }
                        >
                          {run.status ?? "unknown"}
                        </Badge>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>

      {/* =========================================================================
          Compliance & Restricted Platforms Policy
         ========================================================================= */}
      {displayData.restricted_sources && displayData.restricted_sources.length > 0 && (
        <Card className="border bg-card shadow-sm">
          <CardHeader className="p-5 pb-3">
            <div className="flex items-center space-x-2">
              <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-amber-500/10 text-amber-600 dark:text-amber-400">
                <ShieldAlert className="h-4 w-4" />
              </div>
              <div>
                <CardTitle className="text-base font-semibold">
                  Source Access Policy & Compliance Status
                </CardTitle>
                <CardDescription className="text-xs">
                  Evaluation of major platforms per ethical aggregation standards (robots.txt, anti-bot policies, ToS restrictions).
                </CardDescription>
              </div>
            </div>
          </CardHeader>
          <CardContent className="p-0">
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead className="bg-muted/50 text-muted-foreground uppercase tracking-wider font-semibold border-b border-border">
                  <tr>
                    <th className="px-5 py-3">Platform Name</th>
                    <th className="px-5 py-3">Category</th>
                    <th className="px-5 py-3">Access Status</th>
                    <th className="px-5 py-3">Restriction Reason</th>
                    <th className="px-5 py-3">Authorized Path / Alternative</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border">
                  {displayData.restricted_sources.map((r, idx) => (
                    <tr key={idx} className="hover:bg-muted/30 transition-colors">
                      <td className="px-5 py-3.5 font-semibold text-foreground">
                        {r.name}
                      </td>
                      <td className="px-5 py-3.5 text-muted-foreground">
                        {r.type}
                      </td>
                      <td className="px-5 py-3.5">
                        <Badge
                          variant="secondary"
                          className="bg-amber-500/10 text-amber-700 dark:text-amber-400 border-amber-500/20"
                        >
                          Restricted Platform
                        </Badge>
                      </td>
                      <td className="px-5 py-3.5 text-muted-foreground max-w-xs">
                        {r.reason}
                      </td>
                      <td className="px-5 py-3.5 text-foreground font-medium max-w-xs">
                        {r.recommendation}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
