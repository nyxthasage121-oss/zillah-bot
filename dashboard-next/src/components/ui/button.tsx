import * as React from "react";
import { Slot } from "@radix-ui/react-slot";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

const buttonVariants = cva(
  "inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-sm text-sm font-medium ring-offset-background transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50",
  {
    variants: {
      variant: {
        default: "bg-primary text-primary-foreground hover:bg-primary/90",
        destructive: "bg-destructive text-destructive-foreground hover:bg-destructive/90",
        outline: "border border-input bg-background hover:bg-accent hover:text-accent-foreground",
        secondary: "bg-secondary text-secondary-foreground hover:bg-secondary/80",
        ghost: "hover:bg-accent hover:text-accent-foreground",
        link: "text-primary underline-offset-4 hover:underline",
        // Codex variants
        inflict:
          "text-bone shadow-[inset_0_1px_0_rgba(255,200,160,0.25),inset_0_-1px_0_rgba(0,0,0,0.4),0_6px_18px_-6px_rgba(176,48,48,0.55)] border border-gold-bright hover:opacity-95",
        codex:
          "border border-ink-700 bg-ink-900/50 text-bone-muted hover:border-gold hover:text-bone",
      },
      size: {
        default: "h-10 px-4 py-2",
        sm: "h-9 rounded-sm px-3",
        lg: "h-11 rounded-sm px-8",
        icon: "h-10 w-10",
      },
    },
    defaultVariants: { variant: "default", size: "default" },
  }
);

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {
  asChild?: boolean;
}

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, asChild = false, style, ...props }, ref) => {
    const Comp = asChild ? Slot : "button";
    // The inflict gradient lives in inline style so we can avoid a Tailwind plugin
    const inflictStyle: React.CSSProperties | undefined = variant === "inflict"
      ? { background: "linear-gradient(180deg, #b03030 0%, #8a2424 100%)", textShadow: "0 1px 0 rgba(0,0,0,0.4)" }
      : undefined;
    return (
      <Comp
        className={cn(buttonVariants({ variant, size, className }))}
        ref={ref}
        style={{ ...inflictStyle, ...style }}
        {...props}
      />
    );
  }
);
Button.displayName = "Button";

export { Button, buttonVariants };
