import { Slot } from "@radix-ui/react-slot";
import { cva, type VariantProps } from "class-variance-authority";
import { forwardRef, type ButtonHTMLAttributes } from "react";

import { cn } from "@/lib/utils";

/** Chunky buttons with a darker bottom edge that presses down on click. */
const buttonVariants = cva(
  "inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-xl border-2 border-b-4 font-bold transition-[transform,filter,background-color] duration-100 focus-visible:outline-none focus-visible:ring-4 focus-visible:ring-sky/40 active:translate-y-[2px] active:border-b-2 disabled:pointer-events-none disabled:opacity-45",
  {
    variants: {
      variant: {
        default: "border-primary-dark bg-primary text-primary-foreground hover:brightness-105",
        secondary: "border-border border-b-border-strong bg-surface text-ink hover:bg-surface-2",
        outline: "border-border border-b-border-strong bg-transparent text-ink hover:bg-surface-2",
        ghost:
          "border-transparent bg-transparent text-muted hover:bg-surface-2 hover:text-ink active:translate-y-0 active:border-b-4",
        destructive: "border-danger-dark bg-danger-fill text-white hover:brightness-105",
        sky: "border-sky-dark bg-sky text-white hover:brightness-105",
      },
      size: {
        default: "h-11 px-5 text-sm",
        sm: "h-9 px-3.5 text-xs",
        lg: "h-13 px-7 text-base",
        icon: "h-11 w-11 p-0",
      },
    },
    defaultVariants: { variant: "default", size: "default" },
  },
);

export interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement>, VariantProps<typeof buttonVariants> {
  asChild?: boolean;
}

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, asChild = false, ...props }, ref) => {
    const Component = asChild ? Slot : "button";
    return <Component className={cn(buttonVariants({ variant, size }), className)} ref={ref} {...props} />;
  },
);
Button.displayName = "Button";
