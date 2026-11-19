"use client";

import * as React from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { Menu, Rocket, Shield } from "lucide-react";

import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { ThemeToggle } from "@/components/theme-toggle";
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetTrigger,
} from "@/components/ui/sheet";

export function Navbar() {
  const pathname = usePathname();
  const [isOpen, setIsOpen] = React.useState(false);

  const navLinks = [
    { href: "/", label: "Explore Jobs" },
    { href: "/about", label: "About" },
    { href: "/admin", label: "Admin" },
  ];

  return (
    <header className="sticky top-0 z-40 w-full border-b border-border/60 bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
      <div className="container flex h-16 max-w-7xl items-center justify-between px-4 sm:px-8">
        {/* Brand Logo */}
        <Link
          href="/"
          className="flex items-center space-x-2.5 transition-opacity hover:opacity-90"
        >
          <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-primary text-primary-foreground shadow-sm">
            <Rocket className="h-5 w-5" />
          </div>
          <div className="flex flex-col">
            <span className="text-lg font-bold tracking-tight text-foreground">
              Launch<span className="text-primary">Board</span>
            </span>
            <span className="hidden text-[10px] font-medium tracking-wide text-muted-foreground sm:inline-block">
              India Fresher Jobs & Internships
            </span>
          </div>
        </Link>

        {/* Desktop Nav Items */}
        <nav className="hidden items-center space-x-6 md:flex">
          {navLinks.map((link) => {
            const isActive = pathname === link.href;
            return (
              <Link
                key={link.href}
                href={link.href}
                className={cn(
                  "text-sm font-medium transition-colors hover:text-primary",
                  isActive
                    ? "text-primary font-semibold"
                    : "text-muted-foreground"
                )}
              >
                {link.label}
              </Link>
            );
          })}
        </nav>

        {/* Desktop Actions */}
        <div className="hidden items-center space-x-3 md:flex">
          <ThemeToggle />
          <Button asChild size="sm" className="font-medium shadow-sm">
            <Link href="/#jobs-list">Find Opportunities</Link>
          </Button>
        </div>

        {/* Mobile Hamburger Menu */}
        <div className="flex items-center space-x-2 md:hidden">
          <ThemeToggle />
          <Sheet open={isOpen} onOpenChange={setIsOpen}>
            <SheetTrigger asChild>
              <Button variant="ghost" size="icon" aria-label="Open Menu">
                <Menu className="h-5 w-5" />
              </Button>
            </SheetTrigger>
            <SheetContent side="right" className="w-[280px] sm:w-[320px]">
              <SheetHeader className="text-left mb-6">
                <SheetTitle className="flex items-center space-x-2">
                  <div className="flex h-7 w-7 items-center justify-center rounded-md bg-primary text-primary-foreground">
                    <Rocket className="h-4 w-4" />
                  </div>
                  <span>LaunchBoard</span>
                </SheetTitle>
              </SheetHeader>
              <div className="flex flex-col space-y-4">
                {navLinks.map((link) => {
                  const isActive = pathname === link.href;
                  return (
                    <Link
                      key={link.href}
                      href={link.href}
                      onClick={() => setIsOpen(false)}
                      className={cn(
                        "flex items-center rounded-md px-3 py-2 text-sm font-medium transition-colors hover:bg-accent",
                        isActive
                          ? "bg-accent text-primary font-semibold"
                          : "text-muted-foreground"
                      )}
                    >
                      {link.label === "Admin" && (
                        <Shield className="mr-2 h-4 w-4 text-muted-foreground" />
                      )}
                      {link.label}
                    </Link>
                  );
                })}
                <div className="pt-4 border-t border-border">
                  <Button
                    asChild
                    className="w-full"
                    onClick={() => setIsOpen(false)}
                  >
                    <Link href="/#jobs-list">Explore All Jobs</Link>
                  </Button>
                </div>
              </div>
            </SheetContent>
          </Sheet>
        </div>
      </div>
    </header>
  );
}
