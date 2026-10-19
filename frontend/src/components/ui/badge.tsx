import { cva, type VariantProps } from "class-variance-authority";
import type { HTMLAttributes } from "react";

import { cn } from "@/lib/utils";

const badgeVariants = cva("inline-flex items-center gap-1 rounded-full border-2 px-2.5 py-0.5 text-xs font-extrabold", {
  variants: {
    variant: {
      default: "border-primary/30 bg-primary-light text-primary-dark",
      success: "border-success/30 bg-success-light text-success",
      warning: "border-gold/40 bg-gold-light text-warning",
      danger: "border-danger/30 bg-danger-light text-danger",
      teal: "border-sky/30 bg-sky-light text-sky-dark",
      muted: "border-border bg-surface-2 text-muted",
      planner: "border-planner/30 bg-planner-light text-planner-dark",
      auditor: "border-auditor/30 bg-auditor-light text-auditor-dark",
      sentinel: "border-sentinel/40 bg-sentinel-light text-sentinel-dark",
    },
  },
  defaultVariants: { variant: "default" },
});

export interface BadgeProps extends HTMLAttributes<HTMLSpanElement>, VariantProps<typeof badgeVariants> {}

export function Badge({ className, variant, ...props }: BadgeProps) {
  return <span className={cn(badgeVariants({ variant }), className)} {...props} />;
}
