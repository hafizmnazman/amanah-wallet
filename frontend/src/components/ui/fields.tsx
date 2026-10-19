import { forwardRef, type InputHTMLAttributes, type SelectHTMLAttributes, type TextareaHTMLAttributes } from "react";

import { cn } from "@/lib/utils";

const field =
  "w-full rounded-2xl border-2 border-border bg-surface-2 px-4 py-2.5 text-sm font-bold text-ink placeholder:font-semibold placeholder:text-muted transition-colors focus-visible:border-sky focus-visible:bg-surface focus-visible:outline-none disabled:opacity-50";

export const Input = forwardRef<HTMLInputElement, InputHTMLAttributes<HTMLInputElement>>(({ className, ...props }, ref) => (
  <input ref={ref} className={cn(field, "h-11", className)} {...props} />
));
Input.displayName = "Input";

export const Textarea = forwardRef<HTMLTextAreaElement, TextareaHTMLAttributes<HTMLTextAreaElement>>(
  ({ className, ...props }, ref) => <textarea ref={ref} className={cn(field, "min-h-[46px] resize-none", className)} {...props} />,
);
Textarea.displayName = "Textarea";

/** A real <select>, drawn in the theme where the browser allows it (`.themed` in index.css). */
export const Select = forwardRef<HTMLSelectElement, SelectHTMLAttributes<HTMLSelectElement>>(({ className, ...props }, ref) => (
  <select ref={ref} className={cn(field, "themed h-10 cursor-pointer truncate px-3 py-1.5 text-[13px]", className)} {...props} />
));
Select.displayName = "Select";
