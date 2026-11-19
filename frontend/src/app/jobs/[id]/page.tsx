"use client";

import * as React from "react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import {
  ArrowLeft,
  Building2,
  Calendar,
  CheckCircle2,
  ExternalLink,
  Globe,
  MapPin,
  RefreshCw,
  Share2,
  ShieldAlert,
  Sparkles,
  Tag,
  Clock,
} from "lucide-react";
import { format, formatDistanceToNow } from "date-fns";

import { api, Job } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Separator } from "@/components/ui/separator";

export default function JobDetailPage() {
  const params = useParams();
  const router = useRouter();
  const jobId = typeof params?.id === "string" ? params.id : "";

  const [job, setJob] = React.useState<Job | null>(null);
  const [isLoading, setIsLoading] = React.useState(true);
  const [error, setError] = React.useState<string | null>(null);
  const [copied, setCopied] = React.useState(false);

  const fetchJobDetails = React.useCallback(async () => {
    if (!jobId) return;
    setIsLoading(true);
    setError(null);
    try {
      const data = await api.getJob(jobId);
      setJob(data);
    } catch (err) {
      console.error("Failed to load job details:", err);
      setError(
        err instanceof Error
          ? err.message
          : "Unable to find the requested job posting."
      );
    } finally {
      setIsLoading(false);
    }
  }, [jobId]);

  React.useEffect(() => {
    fetchJobDetails();
  }, [fetchJobDetails]);

  const handleShare = () => {
    if (typeof window !== "undefined") {
      navigator.clipboard.writeText(window.location.href);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  const formatDate = (dateStr: string | null | undefined): string => {
    if (!dateStr) return "N/A";
    try {
      const d = new Date(dateStr);
      return format(d, "MMMM d, yyyy");
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

  // Render formatted description safely
  const renderDescription = (text: string) => {
    if (!text) {
      return <p className="text-muted-foreground italic">No description provided.</p>;
    }

    // Check if contains HTML tags
    const hasHtml = /<\/?[a-z][\s\S]*>/i.test(text);
    if (hasHtml) {
      return (
        <div
          className="prose dark:prose-invert max-w-none text-sm sm:text-base leading-relaxed break-words space-y-4 [&_ul]:list-disc [&_ul]:pl-5 [&_ol]:list-decimal [&_ol]:pl-5 [&_li]:mt-1 [&_p]:mb-3 [&_h1]:text-xl [&_h2]:text-lg [&_h3]:text-base [&_a]:text-primary [&_a]:underline"
          dangerouslySetInnerHTML={{ __html: text }}
        />
      );
    }

    // Otherwise render plain text with preserved line breaks
    return (
      <div className="text-sm sm:text-base leading-relaxed text-foreground/90 whitespace-pre-wrap break-words space-y-2">
        {text}
      </div>
    );
  };

  if (isLoading) {
    return (
      <div className="container max-w-5xl px-4 sm:px-8 py-10 space-y-6">
        <div className="flex items-center space-x-2">
          <Skeleton className="h-8 w-28 rounded-md" />
        </div>
        <div className="grid grid-cols-1 gap-8 lg:grid-cols-3">
          <div className="lg:col-span-2 space-y-6">
            <Skeleton className="h-10 w-3/4" />
            <Skeleton className="h-6 w-1/3" />
            <div className="flex gap-2">
              <Skeleton className="h-6 w-20 rounded-full" />
              <Skeleton className="h-6 w-20 rounded-full" />
              <Skeleton className="h-6 w-20 rounded-full" />
            </div>
            <Separator />
            <div className="space-y-3 pt-4">
              <Skeleton className="h-4 w-full" />
              <Skeleton className="h-4 w-full" />
              <Skeleton className="h-4 w-4/5" />
              <Skeleton className="h-4 w-2/3" />
            </div>
          </div>
          <div>
            <Skeleton className="h-64 w-full rounded-xl" />
          </div>
        </div>
      </div>
    );
  }

  if (error || !job) {
    return (
      <div className="container max-w-2xl px-4 py-20 text-center">
        <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-full bg-destructive/10 text-destructive mb-5">
          <ShieldAlert className="h-8 w-8" />
        </div>
        <h1 className="text-2xl font-bold tracking-tight text-foreground">
          Opportunity Not Found
        </h1>
        <p className="mt-2 text-sm text-muted-foreground leading-relaxed">
          {error || "The job posting you are looking for may have expired or been removed."}
        </p>
        <div className="mt-6 flex justify-center gap-3">
          <Button variant="outline" onClick={() => router.push("/")}>
            <ArrowLeft className="mr-2 h-4 w-4" />
            Back to All Jobs
          </Button>
          <Button onClick={fetchJobDetails}>
            <RefreshCw className="mr-2 h-4 w-4" />
            Retry
          </Button>
        </div>
      </div>
    );
  }

  const confidencePercentage =
    job.classification_confidence !== null && job.classification_confidence !== undefined
      ? Math.round(
          job.classification_confidence <= 1
            ? job.classification_confidence * 100
            : job.classification_confidence
        )
      : null;

  return (
    <div className="container max-w-6xl px-4 sm:px-8 py-8 sm:py-12">
      {/* Back button and share button */}
      <div className="mb-6 flex items-center justify-between">
        <Button
          variant="ghost"
          size="sm"
          asChild
          className="text-xs text-muted-foreground hover:text-foreground"
        >
          <Link href="/">
            <ArrowLeft className="mr-1.5 h-4 w-4" />
            Back to Jobs
          </Link>
        </Button>

        <Button
          variant="outline"
          size="sm"
          onClick={handleShare}
          className="text-xs h-8"
        >
          <Share2 className="mr-1.5 h-3.5 w-3.5" />
          {copied ? "Link Copied!" : "Share Opportunity"}
        </Button>
      </div>

      <div className="grid grid-cols-1 gap-8 lg:grid-cols-3">
        {/* Main Content Area */}
        <div className="lg:col-span-2 space-y-8">
          {/* Header Card */}
          <div className="rounded-xl border border-border bg-card p-6 sm:p-8 shadow-sm space-y-4">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <div className="flex items-center space-x-2 text-sm font-semibold text-primary">
                <Building2 className="h-4 w-4" />
                <span>{job.company}</span>
              </div>
              {job.is_remote ? (
                <Badge className="bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border-emerald-500/20">
                  <Globe className="mr-1 h-3 w-3" />
                  Remote in India
                </Badge>
              ) : job.city ? (
                <Badge variant="outline" className="flex items-center gap-1">
                  <MapPin className="h-3 w-3" />
                  {job.city}
                </Badge>
              ) : null}
            </div>

            <h1 className="text-2xl sm:text-3xl font-extrabold tracking-tight text-foreground leading-snug">
              {job.title}
            </h1>

            {/* Badges Bar */}
            <div className="flex flex-wrap items-center gap-2 pt-1">
              {job.role_category && (
                <Badge variant="default" className="bg-primary/10 text-primary border-primary/20 hover:bg-primary/20">
                  {job.role_category}
                </Badge>
              )}
              {job.employment_type && (
                <Badge variant="secondary">{job.employment_type}</Badge>
              )}
              {job.experience_level && (
                <Badge variant="outline">{job.experience_level}</Badge>
              )}
              {confidencePercentage !== null && (
                <Badge
                  variant="outline"
                  className="bg-purple-500/10 text-purple-700 dark:text-purple-300 border-purple-500/20 flex items-center gap-1"
                >
                  <Sparkles className="h-3 w-3" />
                  AI Match: {confidencePercentage}% Confidence
                </Badge>
              )}
            </div>

            {/* Skills pills */}
            {job.skills && job.skills.length > 0 && (
              <div className="pt-2">
                <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-2 flex items-center gap-1">
                  <Tag className="h-3 w-3" />
                  Key Skills & Technologies
                </p>
                <div className="flex flex-wrap gap-1.5">
                  {job.skills.map((skill, idx) => (
                    <Badge
                      key={idx}
                      variant="secondary"
                      className="text-xs px-2.5 py-0.5 bg-muted font-medium text-foreground"
                    >
                      {skill}
                    </Badge>
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* Job Description Card */}
          <Card className="border bg-card shadow-sm">
            <CardHeader className="p-6 sm:p-8 pb-4">
              <CardTitle className="text-xl font-bold">Job Description</CardTitle>
            </CardHeader>
            <Separator />
            <CardContent className="p-6 sm:p-8 pt-6">
              {renderDescription(job.description)}
            </CardContent>
          </Card>

          {/* Verification & Transparency Banner */}
          <div className="rounded-xl border border-border/80 bg-muted/40 p-5 text-xs text-muted-foreground space-y-2">
            <div className="flex items-center space-x-2 font-medium text-foreground">
              <CheckCircle2 className="h-4 w-4 text-emerald-500" />
              <span>LaunchBoard Verification Notice</span>
            </div>
            <p className="leading-relaxed">
              This opportunity was aggregated from <strong>{job.source_name}</strong> and was last
              verified on <strong>{formatDate(job.last_verified_at)}</strong>. While LaunchBoard
              uses AI models to classify fresher status and extract technical skills, job requirements
              and active status are governed solely by the hiring organization.
            </p>
          </div>
        </div>

        {/* Sidebar Actions & Metadata */}
        <div className="space-y-6">
          {/* Apply Now Floating Action Card */}
          <Card className="border bg-card shadow-sm sticky top-24">
            <CardHeader className="p-6 pb-4">
              <CardTitle className="text-lg font-bold">Apply for Position</CardTitle>
            </CardHeader>
            <CardContent className="p-6 pt-0 space-y-5">
              <p className="text-xs text-muted-foreground leading-relaxed">
                You will be redirected to the original application portal on{" "}
                <span className="font-semibold text-foreground">{job.source_name}</span>.
              </p>

              <Button
                asChild
                size="lg"
                className="w-full text-sm font-semibold shadow-md flex items-center justify-center gap-2"
              >
                <a
                  href={job.application_url}
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  Apply Now on Original Site
                  <ExternalLink className="h-4 w-4" />
                </a>
              </Button>

              {job.source_url && (
                <Button
                  variant="outline"
                  size="sm"
                  asChild
                  className="w-full text-xs"
                >
                  <a
                    href={job.source_url}
                    target="_blank"
                    rel="noopener noreferrer"
                  >
                    View Source Listing
                    <ExternalLink className="ml-1 h-3 w-3" />
                  </a>
                </Button>
              )}

              <Separator />

              {/* Opportunity Highlights */}
              <div className="space-y-3.5 text-xs">
                <div className="flex items-start justify-between">
                  <span className="text-muted-foreground flex items-center gap-1.5">
                    <Building2 className="h-3.5 w-3.5" />
                    Company
                  </span>
                  <span className="font-medium text-right text-foreground">{job.company}</span>
                </div>

                <div className="flex items-start justify-between">
                  <span className="text-muted-foreground flex items-center gap-1.5">
                    <MapPin className="h-3.5 w-3.5" />
                    Location
                  </span>
                  <span className="font-medium text-right text-foreground">
                    {job.is_remote ? "Remote (India)" : job.city || job.location || "India"}
                  </span>
                </div>

                <div className="flex items-start justify-between">
                  <span className="text-muted-foreground flex items-center gap-1.5">
                    <Calendar className="h-3.5 w-3.5" />
                    Posted
                  </span>
                  <span className="font-medium text-right text-foreground">
                    {job.posted_at ? formatDate(job.posted_at) : formatDate(job.collected_at)}
                    {job.posted_at && (
                      <span className="block text-[10px] text-muted-foreground">
                        ({formatRelative(job.posted_at)})
                      </span>
                    )}
                  </span>
                </div>

                <div className="flex items-start justify-between">
                  <span className="text-muted-foreground flex items-center gap-1.5">
                    <Clock className="h-3.5 w-3.5" />
                    Last Verified
                  </span>
                  <span className="font-medium text-right text-foreground">
                    {formatDate(job.last_verified_at)}
                  </span>
                </div>

                <div className="flex items-start justify-between">
                  <span className="text-muted-foreground flex items-center gap-1.5">
                    <Tag className="h-3.5 w-3.5" />
                    Source
                  </span>
                  <span className="font-medium text-right text-foreground">{job.source_name}</span>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
