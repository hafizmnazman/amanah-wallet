import { ArrowRight } from "lucide-react";
import type { ReactNode } from "react";
import { Link } from "react-router";

import { cn } from "@/lib/utils";

/** One line after a result or a refusal: what just happened, who stopped it, and where to look next. */
export function WhatHappened({ children, to, label, className }: { children: ReactNode; to?: string; label?: string; className?: string }) {
  return (
    <p data-testid="what-happened" className={cn("flex flex-wrap items-center gap-x-2 gap-y-1 text-sm text-ink", className)}>
      <span>
        <span className="font-extrabold">What just happened:</span> {children}
      </span>
      {to && label && (
        <Link to={to} className="inline-flex items-center gap-1 font-extrabold text-sky-dark hover:underline">
          {label}
          <ArrowRight className="h-4 w-4" aria-hidden />
        </Link>
      )}
    </p>
  );
}
