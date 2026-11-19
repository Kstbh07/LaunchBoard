import Link from "next/link";
import {
  AlertTriangle,
  Bot,
  Calendar,
  CheckCircle2,
  Cpu,
  Database,
  ExternalLink,
  GitBranch,
  Layers,
  Mail,
  RefreshCw,
  Rocket,
  ShieldCheck,
} from "lucide-react";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";

export default function AboutPage() {
  return (
    <div className="container max-w-4xl px-4 sm:px-8 py-12 sm:py-16 space-y-12">
      {/* Page Header */}
      <div className="space-y-4 text-center">
        <div className="inline-flex items-center gap-2 rounded-full border border-primary/20 bg-primary/10 px-3 py-1 text-xs font-medium text-primary">
          <Rocket className="h-3.5 w-3.5" />
          <span>Platform Mission & Architecture</span>
        </div>
        <h1 className="text-3xl sm:text-4xl font-extrabold tracking-tight text-foreground">
          About LaunchBoard
        </h1>
        <p className="text-base sm:text-lg text-muted-foreground max-w-2xl mx-auto leading-relaxed">
          An open, transparent, and AI-powered aggregator built specifically for
          Indian freshers, engineering graduates, and aspiring tech interns.
        </p>
      </div>

      <Separator />

      {/* 1. What is LaunchBoard */}
      <section className="space-y-4">
        <div className="flex items-center space-x-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10 text-primary">
            <Rocket className="h-5 w-5" />
          </div>
          <h2 className="text-2xl font-bold tracking-tight text-foreground">
            1. What is LaunchBoard?
          </h2>
        </div>
        <div className="text-sm sm:text-base text-muted-foreground leading-relaxed space-y-3">
          <p>
            Entry-level job seeking in India is fraught with broken job boards, outdated listings,
            misleading &quot;fresher&quot; titles requiring 3-5 years of experience, and multi-portal
            fragmentation. LaunchBoard solves this by unifying verified fresher jobs and internship
            opportunities into a single, clean interface.
          </p>
          <p>
            LaunchBoard is purpose-built to filter out the noise. We aggregate listings from credible
            developer platforms, tech job boards, and automated RSS feeds, parse them through an
            AI-driven classification pipeline, and eliminate duplicate cross-postings so you only see
            genuine opportunities relevant to early-career developers.
          </p>
        </div>
      </section>

      {/* 2. Data Sources */}
      <section className="space-y-4">
        <div className="flex items-center space-x-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-blue-500/10 text-blue-600 dark:text-blue-400">
            <Database className="h-5 w-5" />
          </div>
          <h2 className="text-2xl font-bold tracking-tight text-foreground">
            2. Data Sources & Transparency
          </h2>
        </div>
        <p className="text-sm sm:text-base text-muted-foreground leading-relaxed">
          We believe in full transparency regarding where our listings originate. LaunchBoard does not
          fabricate job data or act as a private recruitment gatekeeper. Our collectors pull directly
          from public APIs, developer feeds, and corporate ATS platforms:
        </p>
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 pt-2">
          <Card className="border bg-card">
            <CardHeader className="p-4 pb-2">
              <CardTitle className="text-sm font-semibold flex items-center justify-between">
                <span>Public Tech APIs & RSS</span>
                <Badge variant="outline" className="text-[10px]">Open Feeds</Badge>
              </CardTitle>
            </CardHeader>
            <CardContent className="p-4 pt-1 text-xs text-muted-foreground">
              Arbeitnow, Remotive, Himalayas, and curated RSS developer feeds offering remote and India-accessible developer openings.
            </CardContent>
          </Card>

          <Card className="border bg-card">
            <CardHeader className="p-4 pb-2">
              <CardTitle className="text-sm font-semibold flex items-center justify-between">
                <span>ATS & Direct Career Endpoints</span>
                <Badge variant="outline" className="text-[10px]">Direct ATS</Badge>
              </CardTitle>
            </CardHeader>
            <CardContent className="p-4 pt-1 text-xs text-muted-foreground">
              Greenhouse, Lever, and official job board APIs (e.g. Adzuna, Findwork) targeting Indian hubs like Bangalore, Hyderabad, Pune, Mumbai, and Delhi NCR.
            </CardContent>
          </Card>
        </div>
      </section>

      {/* 3. AI Classification */}
      <section className="space-y-4">
        <div className="flex items-center space-x-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-purple-500/10 text-purple-600 dark:text-purple-400">
            <Bot className="h-5 w-5" />
          </div>
          <h2 className="text-2xl font-bold tracking-tight text-foreground">
            3. AI Classification & Skill Extraction
          </h2>
        </div>
        <div className="text-sm sm:text-base text-muted-foreground leading-relaxed space-y-3">
          <p>
            Raw job descriptions are often unstructured and filled with boilerplate text. LaunchBoard
            utilizes Google&apos;s <strong>Gemini API</strong> to read job titles and descriptions in structured batches.
          </p>
          <div className="rounded-xl border border-border bg-card p-4 space-y-2 text-xs sm:text-sm">
            <div className="font-semibold text-foreground flex items-center gap-2">
              <Cpu className="h-4 w-4 text-purple-600" />
              What the AI Pipeline Performs:
            </div>
            <ul className="list-disc pl-5 space-y-1 text-muted-foreground">
              <li>
                <strong>Role Categorization:</strong> Identifies whether the role is Software Engineering,
                Data Science & ML, Frontend, Backend, Full Stack, QA, or DevOps.
              </li>
              <li>
                <strong>Experience Verification:</strong> Determines whether the posting is truly
                intended for <em>Fresher (0-1 yrs)</em> or <em>Internship</em> candidates, discarding senior roles.
              </li>
              <li>
                <strong>Skill Extraction:</strong> Extracts up to 10 concrete programming languages,
                frameworks, and tools (e.g., Python, React, Docker, PostgreSQL, Next.js).
              </li>
              <li>
                <strong>Location & Remote Detection:</strong> Extracts Indian metro cities or flags
                remote availability for candidates located anywhere in India.
              </li>
              <li>
                <strong>Confidence Scoring:</strong> Computes a classification confidence score (0-100%)
                which is displayed transparently on every job listing.
              </li>
            </ul>
          </div>
        </div>
      </section>

      {/* 4. Deduplication */}
      <section className="space-y-4">
        <div className="flex items-center space-x-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-emerald-500/10 text-emerald-600 dark:text-emerald-400">
            <Layers className="h-5 w-5" />
          </div>
          <h2 className="text-2xl font-bold tracking-tight text-foreground">
            4. Smart Deduplication Architecture
          </h2>
        </div>
        <p className="text-sm sm:text-base text-muted-foreground leading-relaxed">
          Companies frequently cross-post the same opening to five different portals. To keep the
          feed clean, LaunchBoard employs a dual-stage deduplication mechanism:
        </p>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs sm:text-sm">
          <div className="rounded-lg border border-border p-4 bg-muted/20">
            <h4 className="font-semibold text-foreground mb-1">Stage 1: Deterministic Fingerprinting</h4>
            <p className="text-muted-foreground">
              SHA-256 hashes constructed from normalized company names, sanitized role titles, and
              canonical location tags. Exact matches are instantly linked to the existing record.
            </p>
          </div>
          <div className="rounded-lg border border-border p-4 bg-muted/20">
            <h4 className="font-semibold text-foreground mb-1">Stage 2: Fuzzy Similarity Matching</h4>
            <p className="text-muted-foreground">
              Token sort and Levenshtein distance matching across job descriptions to catch identical
              openings with slight title variations (e.g. &quot;SDE-1&quot; vs &quot;Software Dev Engineer 1&quot;).
            </p>
          </div>
        </div>
      </section>

      {/* 5. Freshness */}
      <section className="space-y-4">
        <div className="flex items-center space-x-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-amber-500/10 text-amber-600 dark:text-amber-400">
            <RefreshCw className="h-5 w-5" />
          </div>
          <h2 className="text-2xl font-bold tracking-tight text-foreground">
            5. Daily Automated Freshness
          </h2>
        </div>
        <p className="text-sm sm:text-base text-muted-foreground leading-relaxed">
          Aggregated data expires quickly in the fresher job market. LaunchBoard runs automated ingestion
          jobs every day at <strong>6:00 AM IST</strong> via GitHub Actions cron schedules. Each collection run:
        </p>
        <div className="flex flex-wrap gap-2 text-xs">
          <Badge variant="secondary" className="p-2 flex items-center gap-1.5">
            <CheckCircle2 className="h-3.5 w-3.5 text-emerald-500" />
            Fetches latest job listings from all configured sources
          </Badge>
          <Badge variant="secondary" className="p-2 flex items-center gap-1.5">
            <CheckCircle2 className="h-3.5 w-3.5 text-emerald-500" />
            Runs newly found jobs through AI classification
          </Badge>
          <Badge variant="secondary" className="p-2 flex items-center gap-1.5">
            <CheckCircle2 className="h-3.5 w-3.5 text-emerald-500" />
            Updates last_verified_at timestamps for active openings
          </Badge>
        </div>
      </section>

      {/* 6. Limitations */}
      <section id="limitations" className="space-y-4">
        <div className="flex items-center space-x-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-destructive/10 text-destructive">
            <AlertTriangle className="h-5 w-5" />
          </div>
          <h2 className="text-2xl font-bold tracking-tight text-foreground">
            6. Limitations & Disclaimer
          </h2>
        </div>
        <div className="rounded-xl border border-destructive/20 bg-destructive/5 p-5 text-sm space-y-3">
          <p className="text-foreground font-medium">
            Please be mindful of the following when applying through LaunchBoard:
          </p>
          <ul className="list-disc pl-5 space-y-1.5 text-muted-foreground">
            <li>
              <strong>Source Availability:</strong> We rely on public APIs and feeds. If an external
              service experiences downtime or changes its feed format, collection from that source may be delayed.
            </li>
            <li>
              <strong>AI Classification Accuracy:</strong> Although Gemini achieves high accuracy, LLMs can
              occasionally misinterpret a non-standard title, ambiguous experience requirements, or edge-case locations.
            </li>
            <li>
              <strong>Expired Listings:</strong> Companies frequently close job postings without de-listing them
              from their feeds. LaunchBoard updates timestamps daily, but a listing may have closed between refresh cycles.
            </li>
            <li>
              <strong>Independent Verification:</strong> Users should always verify requirements, compensation,
              eligibility, and deadlines on the official employer or applicant portal before applying.
            </li>
          </ul>
        </div>
      </section>

      {/* 7. Report Issues */}
      <section id="report-issues" className="space-y-4">
        <div className="flex items-center space-x-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10 text-primary">
            <Mail className="h-5 w-5" />
          </div>
          <h2 className="text-2xl font-bold tracking-tight text-foreground">
            7. Report Incorrect Listings or Feedback
          </h2>
        </div>
        <p className="text-sm sm:text-base text-muted-foreground leading-relaxed">
          Encountered an expired job, a fraudulent link, or an incorrect classification? We appreciate
          community reports to keep LaunchBoard trustworthy and accurate for all candidates.
        </p>
        <Card className="border bg-card">
          <CardContent className="p-6 space-y-3 text-sm">
            <p className="font-semibold text-foreground">How to submit a report:</p>
            <ol className="list-decimal pl-5 space-y-1 text-muted-foreground">
              <li>Copy the URL of the job detail page on LaunchBoard.</li>
              <li>Provide the specific reason (e.g. &quot;Expired link&quot;, &quot;Requires 5+ years experience&quot;, &quot;Incorrect city&quot;).</li>
              <li>Open an issue on our GitHub repository or contact our automated moderation queue.</li>
            </ol>
            <div className="pt-2 flex flex-wrap gap-3">
              <a
                href="https://github.com"
                target="_blank"
                rel="noreferrer"
                className="inline-flex items-center text-xs font-semibold text-primary hover:underline"
              >
                Open an Issue on GitHub
                <ExternalLink className="ml-1 h-3.5 w-3.5" />
              </a>
            </div>
          </CardContent>
        </Card>
      </section>
    </div>
  );
}
