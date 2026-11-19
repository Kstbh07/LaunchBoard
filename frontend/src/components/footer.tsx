import Link from "next/link";
import { Github, RefreshCw, Rocket } from "lucide-react";

export function Footer() {
  return (
    <footer className="w-full border-t border-border/60 bg-card py-10 text-card-foreground">
      <div className="container max-w-7xl px-4 sm:px-8">
        <div className="grid grid-cols-1 gap-8 md:grid-cols-4">
          {/* Brand info */}
          <div className="space-y-3 md:col-span-2">
            <Link
              href="/"
              className="inline-flex items-center space-x-2 text-lg font-bold tracking-tight"
            >
              <div className="flex h-7 w-7 items-center justify-center rounded-md bg-primary text-primary-foreground">
                <Rocket className="h-4 w-4" />
              </div>
              <span>
                Launch<span className="text-primary">Board</span>
              </span>
            </Link>
            <p className="max-w-md text-sm text-muted-foreground leading-relaxed">
              Your next opportunity starts here. An AI-powered aggregator
              surfacing verified fresher jobs and internship opportunities across
              India from credible engineering & tech sources.
            </p>
            <div className="inline-flex items-center space-x-2 rounded-full bg-muted/60 px-3 py-1 text-xs text-muted-foreground">
              <RefreshCw className="h-3 w-3 animate-spin-reverse text-primary" />
              <span>Data refreshes daily at 6:00 AM IST via automated pipelines</span>
            </div>
          </div>

          {/* Quick links */}
          <div className="space-y-3">
            <h4 className="text-sm font-semibold tracking-wide text-foreground">
              Platform
            </h4>
            <ul className="space-y-2 text-sm text-muted-foreground">
              <li>
                <Link
                  href="/#jobs-list"
                  className="transition-colors hover:text-foreground"
                >
                  Explore Jobs
                </Link>
              </li>
              <li>
                <Link
                  href="/about"
                  className="transition-colors hover:text-foreground"
                >
                  About & Methodology
                </Link>
              </li>
              <li>
                <Link
                  href="/admin"
                  className="transition-colors hover:text-foreground"
                >
                  Admin Portal
                </Link>
              </li>
            </ul>
          </div>

          {/* Resources & Open Source */}
          <div className="space-y-3">
            <h4 className="text-sm font-semibold tracking-wide text-foreground">
              Community
            </h4>
            <ul className="space-y-2 text-sm text-muted-foreground">
              <li>
                <a
                  href="https://github.com"
                  target="_blank"
                  rel="noreferrer"
                  className="inline-flex items-center space-x-1.5 transition-colors hover:text-foreground"
                >
                  <Github className="h-4 w-4" />
                  <span>GitHub Repository</span>
                </a>
              </li>
              <li>
                <Link
                  href="/about#limitations"
                  className="transition-colors hover:text-foreground"
                >
                  Data Transparency
                </Link>
              </li>
              <li>
                <Link
                  href="/about#report-issues"
                  className="transition-colors hover:text-foreground"
                >
                  Report an Issue
                </Link>
              </li>
            </ul>
          </div>
        </div>

        <div className="mt-8 border-t border-border/60 pt-6 flex flex-col items-center justify-between gap-4 text-xs text-muted-foreground sm:flex-row">
          <p>© 2026 LaunchBoard. Built for aspiring engineers and fresh graduates in India.</p>
          <div className="flex space-x-4">
            <Link href="/about" className="hover:underline">
              Terms & Methodology
            </Link>
            <Link href="/about#limitations" className="hover:underline">
              Disclaimer
            </Link>
          </div>
        </div>
      </div>
    </footer>
  );
}
