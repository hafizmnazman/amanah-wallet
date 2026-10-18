import { cva, type VariantProps } from "class-variance-authority";
import type { HTMLAttributes } from "react";

import { cn } from "@/lib/utils";

const badgeVariants = cva("inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-xs font-medium", {
  variants: {
    variant: {
      default: "border-primary/40 bg-primary/15 text-primary",
      success: "border-success/40 bg-success/15 text-success",
      warning: "border-warning/40 bg-warning/15 text-warning",
      danger: "border-danger/40 bg-danger/15 text-danger",
      teal: "border-teal/40 bg-teal/15 text-teal",
      muted: "border-border bg-surface-2 text-muted",
    },
  },
  defaultVariants: { variant: "default" },
});

export interface BadgeProps extends HTMLAttributes<HTMLSpanElement>, VariantProps<typeof badgeVariants> {}

export function Badge({ className, variant, ...props }: BadgeProps) {
  return <span className={cn(badgeVariants({ variant }), className)} {...props} />;
}
