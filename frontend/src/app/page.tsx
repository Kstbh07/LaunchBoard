"use client";

import * as React from "react";
import Link from "next/link";
import {
  Award,
  Briefcase,
  Building2,
  Calendar,
  CheckCircle2,
  ExternalLink,
  Filter,
  Globe,
  GraduationCap,
  MapPin,
  RefreshCw,
  RotateCcw,
  Search,
  Sparkles,
  X,
} from "lucide-react";
import { formatDistanceToNow, format } from "date-fns";

import { api, Job, RoleCount, CityCount, Stats } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardFooter, CardHeader } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Switch } from "@/components/ui/switch";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

export default function HomePage() {
  // State for search and filters
  const [searchQuery, setSearchQuery] = React.useState("");
  const [debouncedQuery, setDebouncedQuery] = React.useState("");
  const [selectedRole, setSelectedRole] = React.useState("all");
  const [selectedCity, setSelectedCity] = React.useState("all");
  const [selectedEmploymentType, setSelectedEmploymentType] = React.useState("all");
  const [selectedExperienceLevel, setSelectedExperienceLevel] = React.useState("all");
  const [isRemoteOnly, setIsRemoteOnly] = React.useState(false);
  const [sortBy, setSortBy] = React.useState("posted_at");
  const [page, setPage] = React.useState(1);
  const pageSize = 12;

  // Data states
  const [jobs, setJobs] = React.useState<Job[]>([]);
  const [totalJobs, setTotalJobs] = React.useState(0);
  const [totalPages, setTotalPages] = React.useState(1);
  const [roles, setRoles] = React.useState<RoleCount[]>([]);
  const [cities, setCities] = React.useState<CityCount[]>([]);
  const [stats, setStats] = React.useState<Stats | null>(null);

  // Status states
  const [isLoadingJobs, setIsLoadingJobs] = React.useState(true);
  const [isLoadingStats, setIsLoadingStats] = React.useState(true);
  const [errorMessage, setErrorMessage] = React.useState<string | null>(null);

  // Debounce search query
  React.useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedQuery(searchQuery);
      setPage(1);
    }, 350);
    return () => clearTimeout(timer);
  }, [searchQuery]);

  // Fetch roles, cities, and stats on mount
  const fetchMetadata = React.useCallback(async () => {
    setIsLoadingStats(true);
    try {
      const [statsData, rolesData, citiesData] = await Promise.allSettled([
        api.getStats(),
        api.getRoles(),
        api.getCities(),
      ]);

      if (statsData.status === "fulfilled") {
        setStats(statsData.value);
      }
      if (rolesData.status === "fulfilled") {
        setRoles(rolesData.value);
      }
      if (citiesData.status === "fulfilled") {
        setCities(citiesData.value);
      }
    } catch (err) {
      console.warn("Failed to fetch metadata:", err);
    } finally {
      setIsLoadingStats(false);
    }
  }, []);

  React.useEffect(() => {
    fetchMetadata();
  }, [fetchMetadata]);

  // Fetch jobs
  const fetchJobs = React.useCallback(async () => {
    setIsLoadingJobs(true);
    setErrorMessage(null);
    try {
      const response = await api.getJobs({
        q: debouncedQuery || undefined,
        role_category: selectedRole !== "all" ? selectedRole : undefined,
        city: selectedCity !== "all" ? selectedCity : undefined,
        employment_type: selectedEmploymentType !== "all" ? selectedEmploymentType : undefined,
        experience_level: selectedExperienceLevel !== "all" ? selectedExperienceLevel : undefined,
        is_remote: isRemoteOnly ? true : undefined,
        sort_by: sortBy,
        sort_order: sortBy === "title" || sortBy === "company" ? "asc" : "desc",
        page,
        page_size: pageSize,
      });

      setJobs(response.jobs || []);
      setTotalJobs(response.total || 0);
      setTotalPages(response.total_pages || Math.max(1, Math.ceil((response.total || 0) / pageSize)));
    } catch (err) {
      console.error("Error fetching jobs:", err);
      setErrorMessage(
        err instanceof Error ? err.message : "Unable to load jobs at this moment."
      );
    } finally {
      setIsLoadingJobs(false);
    }
  }, [
    debouncedQuery,
    selectedRole,
    selectedCity,
    selectedEmploymentType,
    selectedExperienceLevel,
    isRemoteOnly,
    sortBy,
    page,
    pageSize,
  ]);

  React.useEffect(() => {
    fetchJobs();
  }, [fetchJobs]);

  // Reset all filters
  const handleClearFilters = () => {
    setSearchQuery("");
    setDebouncedQuery("");
    setSelectedRole("all");
    setSelectedCity("all");
    setSelectedEmploymentType("all");
    setSelectedExperienceLevel("all");
    setIsRemoteOnly(false);
    setSortBy("posted_at");
    setPage(1);
  };

  const hasActiveFilters =
    debouncedQuery !== "" ||
    selectedRole !== "all" ||
    selectedCity !== "all" ||
    selectedEmploymentType !== "all" ||
    selectedExperienceLevel !== "all" ||
    isRemoteOnly;

  // Helper date formatter
  const formatJobDate = (dateStr: string | null | undefined): string => {
    if (!dateStr) return "Recently added";
    try {
      const d = new Date(dateStr);
      return formatDistanceToNow(d, { addSuffix: true });
    } catch {
      return "Recently added";
    }
  };

  const formatVerifiedDate = (dateStr: string | null | undefined): string => {
    if (!dateStr) return "Today";
    try {
      const d = new Date(dateStr);
      return format(d, "MMM d, yyyy");
    } catch {
      return "Verified";
    }
  };

  // Badge color helper for role categories
  const getRoleBadgeVariant = (role: string | null): string => {
    if (!role) return "bg-slate-100 text-slate-800 dark:bg-slate-800 dark:text-slate-200";
    const lower = role.toLowerCase();
    if (lower.includes("software") || lower.includes("backend") || lower.includes("frontend") || lower.includes("full stack")) {
      return "bg-blue-100 text-blue-800 dark:bg-blue-950/60 dark:text-blue-300 border-blue-200 dark:border-blue-900";
    }
    if (lower.includes("data") || lower.includes("ai") || lower.includes("ml") || lower.includes("learning")) {
      return "bg-purple-100 text-purple-800 dark:bg-purple-950/60 dark:text-purple-300 border-purple-200 dark:border-purple-900";
    }
    if (lower.includes("devops") || lower.includes("cloud") || lower.includes("sysadmin")) {
      return "bg-teal-100 text-teal-800 dark:bg-teal-950/60 dark:text-teal-300 border-teal-200 dark:border-teal-900";
    }
    if (lower.includes("design") || lower.includes("product") || lower.includes("ui") || lower.includes("ux")) {
      return "bg-rose-100 text-rose-800 dark:bg-rose-950/60 dark:text-rose-300 border-rose-200 dark:border-rose-900";
    }
    if (lower.includes("qa") || lower.includes("test")) {
      return "bg-amber-100 text-amber-800 dark:bg-amber-950/60 dark:text-amber-300 border-amber-200 dark:border-amber-900";
    }
    return "bg-indigo-100 text-indigo-800 dark:bg-indigo-950/60 dark:text-indigo-300 border-indigo-200 dark:border-indigo-900";
  };

  return (
    <div className="flex flex-col min-h-screen">
      {/* =========================================================================
          A. Hero Section
         ========================================================================= */}
      <section className="relative overflow-hidden border-b border-border/50 bg-gradient-to-b from-primary/5 via-background to-background py-16 sm:py-24">
        <div className="container max-w-5xl px-4 sm:px-8 text-center relative z-10">
          <div className="inline-flex items-center gap-2 rounded-full border border-primary/20 bg-primary/10 px-3.5 py-1 text-xs font-medium text-primary mb-6 shadow-sm">
            <Sparkles className="h-3.5 w-3.5" />
            <span>AI-Curated Fresher & Internship Aggregator</span>
          </div>

          <h1 className="text-4xl font-extrabold tracking-tight sm:text-5xl lg:text-6xl text-foreground">
            Your next opportunity <span className="text-primary">starts here.</span>
          </h1>

          <p className="mt-4 max-w-2xl mx-auto text-base sm:text-lg text-muted-foreground leading-relaxed">
            Discover verified fresher jobs and internships across India, collected from
            opportunities that matter — filtered by AI for real entry-level experience.
          </p>

          {/* Prominent Hero Search Bar */}
          <div className="mt-8 max-w-2xl mx-auto">
            <div className="relative flex items-center shadow-md rounded-xl bg-card border border-border p-1.5 focus-within:ring-2 focus-within:ring-primary focus-within:border-transparent transition-all">
              <Search className="ml-3 h-5 w-5 text-muted-foreground" />
              <Input
                type="text"
                placeholder="Search job title, company, or tech stack (e.g., Python, React, SDE Intern)..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="border-0 bg-transparent shadow-none focus-visible:ring-0 text-sm sm:text-base px-3 h-11"
              />
              {searchQuery && (
                <Button
                  variant="ghost"
                  size="icon"
                  className="h-8 w-8 text-muted-foreground hover:text-foreground"
                  onClick={() => setSearchQuery("")}
                >
                  <X className="h-4 w-4" />
                </Button>
              )}
              <Button
                size="default"
                className="h-10 px-5 rounded-lg shadow-sm font-medium"
                onClick={() => {
                  setDebouncedQuery(searchQuery);
                  setPage(1);
                  const el = document.getElementById("jobs-list");
                  if (el) el.scrollIntoView({ behavior: "smooth" });
                }}
              >
                Search
              </Button>
            </div>
            {/* Quick search tags */}
            <div className="mt-3 flex flex-wrap items-center justify-center gap-1.5 text-xs text-muted-foreground">
              <span className="font-medium mr-1">Popular:</span>
              {["Frontend Developer", "Backend Engineer", "Data Analyst", "SDE Intern", "Bangalore", "Remote"].map(
                (tag) => (
                  <button
                    key={tag}
                    onClick={() => {
                      setSearchQuery(tag);
                      setDebouncedQuery(tag);
                      setPage(1);
                    }}
                    className="rounded-full bg-secondary px-2.5 py-0.5 font-medium transition-colors hover:bg-secondary/80 hover:text-foreground"
                  >
                    {tag}
                  </button>
                )
              )}
            </div>
          </div>
        </div>
      </section>

      {/* =========================================================================
          B. Stats Bar
         ========================================================================= */}
      <section className="border-b border-border/60 bg-card/60 py-8">
        <div className="container max-w-7xl px-4 sm:px-8">
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-6">
            {/* Total Opportunities */}
            <Card className="border bg-card/50 shadow-none">
              <CardContent className="flex items-center space-x-3 p-4">
                <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-blue-500/10 text-primary">
                  <Briefcase className="h-5 w-5" />
                </div>
                <div>
                  <p className="text-[11px] font-medium uppercase tracking-wider text-muted-foreground">
                    Opportunities
                  </p>
                  {isLoadingStats ? (
                    <Skeleton className="h-6 w-14 mt-1" />
                  ) : (
                    <p className="text-xl font-bold tracking-tight text-foreground">
                      {stats?.total_active_jobs?.toLocaleString() ?? totalJobs}
                    </p>
                  )}
                </div>
              </CardContent>
            </Card>

            {/* Internships */}
            <Card className="border bg-card/50 shadow-none">
              <CardContent className="flex items-center space-x-3 p-4">
                <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-indigo-500/10 text-indigo-600 dark:text-indigo-400">
                  <Award className="h-5 w-5" />
                </div>
                <div>
                  <p className="text-[11px] font-medium uppercase tracking-wider text-muted-foreground">
                    Internships
                  </p>
                  {isLoadingStats ? (
                    <Skeleton className="h-6 w-14 mt-1" />
                  ) : (
                    <p className="text-xl font-bold tracking-tight text-foreground">
                      {stats?.total_internships?.toLocaleString() ?? 0}
                    </p>
                  )}
                </div>
              </CardContent>
            </Card>

            {/* Fresher Roles */}
            <Card className="border bg-card/50 shadow-none">
              <CardContent className="flex items-center space-x-3 p-4">
                <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-teal-500/10 text-teal-600 dark:text-teal-400">
                  <GraduationCap className="h-5 w-5" />
                </div>
                <div>
                  <p className="text-[11px] font-medium uppercase tracking-wider text-muted-foreground">
                    Fresher Roles
                  </p>
                  {isLoadingStats ? (
                    <Skeleton className="h-6 w-14 mt-1" />
                  ) : (
                    <p className="text-xl font-bold tracking-tight text-foreground">
                      {stats?.total_fresher_jobs?.toLocaleString() ?? 0}
                    </p>
                  )}
                </div>
              </CardContent>
            </Card>

            {/* Companies */}
            <Card className="border bg-card/50 shadow-none">
              <CardContent className="flex items-center space-x-3 p-4">
                <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-purple-500/10 text-purple-600 dark:text-purple-400">
                  <Building2 className="h-5 w-5" />
                </div>
                <div>
                  <p className="text-[11px] font-medium uppercase tracking-wider text-muted-foreground">
                    Companies
                  </p>
                  {isLoadingStats ? (
                    <Skeleton className="h-6 w-14 mt-1" />
                  ) : (
                    <p className="text-xl font-bold tracking-tight text-foreground">
                      {stats?.total_companies?.toLocaleString() ?? 0}
                    </p>
                  )}
                </div>
              </CardContent>
            </Card>

            {/* Cities */}
            <Card className="border bg-card/50 shadow-none">
              <CardContent className="flex items-center space-x-3 p-4">
                <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-emerald-500/10 text-emerald-600 dark:text-emerald-400">
                  <MapPin className="h-5 w-5" />
                </div>
                <div>
                  <p className="text-[11px] font-medium uppercase tracking-wider text-muted-foreground">
                    Tech Hubs
                  </p>
                  {isLoadingStats ? (
                    <Skeleton className="h-6 w-14 mt-1" />
                  ) : (
                    <p className="text-xl font-bold tracking-tight text-foreground">
                      {stats?.total_cities ?? (cities.length > 0 ? cities.length : 0)}
                    </p>
                  )}
                </div>
              </CardContent>
            </Card>

            {/* Remote Jobs */}
            <Card className="border bg-card/50 shadow-none">
              <CardContent className="flex items-center space-x-3 p-4">
                <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-amber-500/10 text-amber-600 dark:text-amber-400">
                  <Globe className="h-5 w-5" />
                </div>
                <div>
                  <p className="text-[11px] font-medium uppercase tracking-wider text-muted-foreground">
                    Remote Roles
                  </p>
                  {isLoadingStats ? (
                    <Skeleton className="h-6 w-14 mt-1" />
                  ) : (
                    <p className="text-xl font-bold tracking-tight text-foreground">
                      {stats?.total_remote_jobs?.toLocaleString() ?? 0}
                    </p>
                  )}
                </div>
              </CardContent>
            </Card>
          </div>
        </div>
      </section>

      {/* =========================================================================
          C. Filters Toolbar & Main Job Feed
         ========================================================================= */}
      <section id="jobs-list" className="flex-1 py-10">
        <div className="container max-w-7xl px-4 sm:px-8">
          {/* Section Header */}
          <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between pb-6">
            <div>
              <h2 className="text-2xl font-bold tracking-tight text-foreground">
                Verified Job Openings
              </h2>
              <p className="text-sm text-muted-foreground">
                Showing {totalJobs > 0 ? (page - 1) * pageSize + 1 : 0} -{" "}
                {Math.min(page * pageSize, totalJobs)} of {totalJobs} verified listings
              </p>
            </div>

            {hasActiveFilters && (
              <Button
                variant="outline"
                size="sm"
                onClick={handleClearFilters}
                className="self-start md:self-auto text-xs"
              >
                <RotateCcw className="mr-1.5 h-3.5 w-3.5" />
                Reset Filters
              </Button>
            )}
          </div>

          {/* Filters Bar Card */}
          <div className="rounded-xl border border-border bg-card p-4 sm:p-5 shadow-sm mb-8 space-y-4">
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4">
              {/* Role Category Dropdown */}
              <div className="space-y-1.5">
                <Label className="text-xs font-medium text-muted-foreground">
                  Role Category
                </Label>
                <Select
                  value={selectedRole}
                  onValueChange={(val) => {
                    setSelectedRole(val);
                    setPage(1);
                  }}
                >
                  <SelectTrigger className="h-9">
                    <SelectValue placeholder="All Categories" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">All Categories</SelectItem>
                    {roles.length > 0 ? (
                      roles.map((r) => (
                        <SelectItem key={r.role_category} value={r.role_category}>
                          {r.role_category} ({r.count})
                        </SelectItem>
                      ))
                    ) : (
                      <>
                        <SelectItem value="Software Engineering">
                          Software Engineering
                        </SelectItem>
                        <SelectItem value="Frontend">Frontend</SelectItem>
                        <SelectItem value="Backend">Backend</SelectItem>
                        <SelectItem value="Full Stack">Full Stack</SelectItem>
                        <SelectItem value="Data Science & ML">
                          Data Science & ML
                        </SelectItem>
                        <SelectItem value="DevOps & Cloud">
                          DevOps & Cloud
                        </SelectItem>
                      </>
                    )}
                  </SelectContent>
                </Select>
              </div>

              {/* City Dropdown */}
              <div className="space-y-1.5">
                <Label className="text-xs font-medium text-muted-foreground">
                  Location / City
                </Label>
                <Select
                  value={selectedCity}
                  onValueChange={(val) => {
                    setSelectedCity(val);
                    setPage(1);
                  }}
                >
                  <SelectTrigger className="h-9">
                    <SelectValue placeholder="All Locations" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">All Locations</SelectItem>
                    {cities.length > 0 ? (
                      cities.map((c) => (
                        <SelectItem key={c.city} value={c.city}>
                          {c.city} ({c.count})
                        </SelectItem>
                      ))
                    ) : (
                      <>
                        <SelectItem value="Bangalore">Bangalore</SelectItem>
                        <SelectItem value="Hyderabad">Hyderabad</SelectItem>
                        <SelectItem value="Pune">Pune</SelectItem>
                        <SelectItem value="Mumbai">Mumbai</SelectItem>
                        <SelectItem value="Delhi NCR">Delhi NCR</SelectItem>
                        <SelectItem value="Chennai">Chennai</SelectItem>
                      </>
                    )}
                  </SelectContent>
                </Select>
              </div>

              {/* Employment Type Dropdown */}
              <div className="space-y-1.5">
                <Label className="text-xs font-medium text-muted-foreground">
                  Employment Type
                </Label>
                <Select
                  value={selectedEmploymentType}
                  onValueChange={(val) => {
                    setSelectedEmploymentType(val);
                    setPage(1);
                  }}
                >
                  <SelectTrigger className="h-9">
                    <SelectValue placeholder="All Employment Types" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">All Types</SelectItem>
                    <SelectItem value="Internship">Internship</SelectItem>
                    <SelectItem value="Full-time">Full-time</SelectItem>
                    <SelectItem value="Part-time">Part-time</SelectItem>
                    <SelectItem value="Contract">Contract</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              {/* Experience Level Dropdown */}
              <div className="space-y-1.5">
                <Label className="text-xs font-medium text-muted-foreground">
                  Experience Level
                </Label>
                <Select
                  value={selectedExperienceLevel}
                  onValueChange={(val) => {
                    setSelectedExperienceLevel(val);
                    setPage(1);
                  }}
                >
                  <SelectTrigger className="h-9">
                    <SelectValue placeholder="All Experience Levels" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">All Levels</SelectItem>
                    <SelectItem value="Fresher">Fresher (0-1 yrs)</SelectItem>
                    <SelectItem value="Internship">Internship</SelectItem>
                    <SelectItem value="Entry-level">Entry-level (0-2 yrs)</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>

            {/* Secondary toolbar options: Sort by & Remote Toggle */}
            <div className="flex flex-wrap items-center justify-between gap-4 pt-3 border-t border-border/60">
              <div className="flex items-center space-x-2">
                <Switch
                  id="remote-only-filter"
                  checked={isRemoteOnly}
                  onCheckedChange={(checked) => {
                    setIsRemoteOnly(checked);
                    setPage(1);
                  }}
                />
                <Label
                  htmlFor="remote-only-filter"
                  className="text-xs font-medium cursor-pointer"
                >
                  Remote Only
                </Label>
              </div>

              <div className="flex items-center space-x-2 ml-auto">
                <Label className="text-xs font-medium text-muted-foreground whitespace-nowrap">
                  Sort by:
                </Label>
                <Select
                  value={sortBy}
                  onValueChange={(val) => {
                    setSortBy(val);
                    setPage(1);
                  }}
                >
                  <SelectTrigger className="h-8 w-[140px] text-xs">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent align="end">
                    <SelectItem value="posted_at">Posted Date</SelectItem>
                    <SelectItem value="collected_at">Latest Added</SelectItem>
                    <SelectItem value="company">Company (A-Z)</SelectItem>
                    <SelectItem value="title">Title (A-Z)</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>
          </div>

          {/* =========================================================================
              D. Job Cards Grid
             ========================================================================= */}
          {isLoadingJobs ? (
            /* Loading State: 6 Skeleton Cards */
            <div className="grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-3">
              {Array.from({ length: 6 }).map((_, idx) => (
                <Card key={idx} className="flex flex-col justify-between p-5 space-y-4">
                  <div className="space-y-3">
                    <div className="flex items-center justify-between">
                      <Skeleton className="h-4 w-28" />
                      <Skeleton className="h-5 w-16 rounded-full" />
                    </div>
                    <Skeleton className="h-6 w-3/4" />
                    <Skeleton className="h-4 w-1/2" />
                    <div className="flex gap-2 pt-2">
                      <Skeleton className="h-5 w-14 rounded-md" />
                      <Skeleton className="h-5 w-14 rounded-md" />
                      <Skeleton className="h-5 w-14 rounded-md" />
                    </div>
                  </div>
                  <div className="pt-4 border-t border-border/60 flex items-center justify-between">
                    <Skeleton className="h-4 w-24" />
                    <Skeleton className="h-8 w-20 rounded-md" />
                  </div>
                </Card>
              ))}
            </div>
          ) : errorMessage ? (
            /* Error State with Retry Button */
            <div className="rounded-xl border border-destructive/20 bg-destructive/5 p-12 text-center">
              <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-destructive/10 text-destructive mb-4">
                <X className="h-6 w-6" />
              </div>
              <h3 className="text-lg font-semibold text-foreground">
                Unable to load job listings
              </h3>
              <p className="mt-2 text-sm text-muted-foreground max-w-md mx-auto">
                {errorMessage}
              </p>
              <div className="mt-6 flex justify-center gap-3">
                <Button
                  onClick={fetchJobs}
                  className="shadow-sm"
                >
                  <RefreshCw className="mr-2 h-4 w-4" />
                  Retry Loading
                </Button>
                {hasActiveFilters && (
                  <Button variant="outline" onClick={handleClearFilters}>
                    Clear Filters
                  </Button>
                )}
              </div>
            </div>
          ) : jobs.length === 0 ? (
            /* Empty State: No results */
            <div className="rounded-xl border border-dashed border-border p-12 text-center bg-card/40">
              <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-muted text-muted-foreground mb-4">
                <Filter className="h-6 w-6" />
              </div>
              <h3 className="text-lg font-semibold text-foreground">
                No matching opportunities found
              </h3>
              <p className="mt-2 text-sm text-muted-foreground max-w-md mx-auto leading-relaxed">
                We couldn&apos;t find any active fresher roles matching your current filter criteria.
                Try broadening your search or resetting filters to see all available openings.
              </p>
              <div className="mt-6">
                <Button onClick={handleClearFilters} variant="default" className="shadow-sm">
                  <RotateCcw className="mr-2 h-4 w-4" />
                  Clear All Filters
                </Button>
              </div>
            </div>
          ) : (
            /* Actual Job Cards Grid */
            <div className="grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-3">
              {jobs.map((job) => {
                const skillsList = Array.isArray(job.skills) ? job.skills : [];
                const visibleSkills = skillsList.slice(0, 4);
                const remainingSkillsCount = skillsList.length - visibleSkills.length;

                return (
                  <Card
                    key={job.id}
                    className="group flex flex-col justify-between border bg-card transition-all duration-200 hover:-translate-y-0.5 hover:shadow-md hover:border-primary/40 rounded-xl"
                  >
                    <div>
                      <CardHeader className="p-5 pb-3 space-y-2.5">
                        {/* Company Name & Badges */}
                        <div className="flex items-center justify-between gap-2">
                          <div className="flex items-center space-x-1.5 text-xs font-semibold text-muted-foreground truncate">
                            <Building2 className="h-3.5 w-3.5 shrink-0 text-primary" />
                            <span className="truncate">{job.company}</span>
                          </div>
                          {job.is_remote ? (
                            <Badge
                              variant="secondary"
                              className="bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/20 text-[10px] shrink-0"
                            >
                              Remote
                            </Badge>
                          ) : job.city ? (
                            <Badge
                              variant="outline"
                              className="text-[10px] shrink-0 flex items-center gap-1"
                            >
                              <MapPin className="h-2.5 w-2.5" />
                              {job.city}
                            </Badge>
                          ) : null}
                        </div>

                        {/* Job Title */}
                        <Link
                          href={`/jobs/${job.id}`}
                          className="block text-base font-semibold leading-snug tracking-tight text-foreground group-hover:text-primary transition-colors line-clamp-2"
                        >
                          {job.title}
                        </Link>

                        {/* Meta Badges: Role Category, Employment Type, Experience Level */}
                        <div className="flex flex-wrap items-center gap-1.5 pt-1">
                          {job.role_category && (
                            <span
                              className={`inline-flex items-center px-2 py-0.5 rounded text-[11px] font-medium border ${getRoleBadgeVariant(
                                job.role_category
                              )}`}
                            >
                              {job.role_category}
                            </span>
                          )}
                          {job.employment_type && (
                            <Badge variant="secondary" className="text-[10px]">
                              {job.employment_type}
                            </Badge>
                          )}
                          {job.experience_level && (
                            <Badge variant="outline" className="text-[10px]">
                              {job.experience_level}
                            </Badge>
                          )}
                        </div>
                      </CardHeader>

                      <CardContent className="p-5 pt-0 pb-4">
                        {/* Skills Badges */}
                        {skillsList.length > 0 && (
                          <div className="mt-2 flex flex-wrap gap-1">
                            {visibleSkills.map((skill, sIdx) => (
                              <span
                                key={sIdx}
                                className="inline-block rounded-md bg-muted px-2 py-0.5 text-[10px] font-medium text-muted-foreground"
                              >
                                {skill}
                              </span>
                            ))}
                            {remainingSkillsCount > 0 && (
                              <span className="inline-block rounded-md bg-muted/60 px-1.5 py-0.5 text-[10px] font-medium text-muted-foreground">
                                +{remainingSkillsCount}
                              </span>
                            )}
                          </div>
                        )}

                        {/* Posted / Collected & Source Info */}
                        <div className="mt-4 flex flex-col space-y-1 text-xs text-muted-foreground">
                          <div className="flex items-center space-x-1.5">
                            <Calendar className="h-3 w-3 text-muted-foreground/70" />
                            <span>
                              {job.posted_at
                                ? `Posted ${formatJobDate(job.posted_at)}`
                                : `Collected ${formatJobDate(job.collected_at)}`}
                            </span>
                          </div>
                          <div className="flex items-center justify-between text-[11px] text-muted-foreground/80 pt-1">
                            <span>
                              Via <strong className="font-medium text-foreground">{job.source_name}</strong>
                            </span>
                            <span className="flex items-center gap-1 text-[10px]">
                              <CheckCircle2 className="h-3 w-3 text-emerald-500" />
                              {formatVerifiedDate(job.last_verified_at)}
                            </span>
                          </div>
                        </div>
                      </CardContent>
                    </div>

                    {/* Card Footer with Details link & Apply Now */}
                    <CardFooter className="p-5 pt-3 border-t border-border/60 flex items-center justify-between gap-2 bg-muted/20">
                      <Button
                        variant="ghost"
                        size="sm"
                        asChild
                        className="text-xs font-medium px-2.5 h-8 text-muted-foreground hover:text-foreground"
                      >
                        <Link href={`/jobs/${job.id}`}>View Details</Link>
                      </Button>
                      <Button
                        size="sm"
                        asChild
                        className="text-xs font-semibold px-3 h-8 shadow-sm gap-1"
                      >
                        <a
                          href={job.application_url}
                          target="_blank"
                          rel="noopener noreferrer"
                        >
                          Apply Now
                          <ExternalLink className="h-3 w-3" />
                        </a>
                      </Button>
                    </CardFooter>
                  </Card>
                );
              })}
            </div>
          )}

          {/* =========================================================================
              E. Pagination
             ========================================================================= */}
          {!isLoadingJobs && totalPages > 1 && (
            <div className="mt-12 flex flex-col sm:flex-row items-center justify-between gap-4 border-t border-border/60 pt-6">
              <p className="text-xs sm:text-sm text-muted-foreground">
                Showing{" "}
                <span className="font-medium text-foreground">
                  {(page - 1) * pageSize + 1}
                </span>{" "}
                to{" "}
                <span className="font-medium text-foreground">
                  {Math.min(page * pageSize, totalJobs)}
                </span>{" "}
                of{" "}
                <span className="font-medium text-foreground">{totalJobs}</span>{" "}
                results
              </p>

              <div className="flex items-center space-x-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => {
                    setPage((p) => Math.max(1, p - 1));
                    window.scrollTo({ top: 380, behavior: "smooth" });
                  }}
                  disabled={page <= 1}
                  className="h-8 text-xs"
                >
                  Previous
                </Button>
                <div className="text-xs font-medium px-2 text-muted-foreground">
                  Page <span className="font-bold text-foreground">{page}</span> of{" "}
                  <span className="font-bold text-foreground">{totalPages}</span>
                </div>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => {
                    setPage((p) => Math.min(totalPages, p + 1));
                    window.scrollTo({ top: 380, behavior: "smooth" });
                  }}
                  disabled={page >= totalPages}
                  className="h-8 text-xs"
                >
                  Next
                </Button>
              </div>
            </div>
          )}
        </div>
      </section>
    </div>
  );
}
