import * as React from "react";
import { cn } from "@/lib/utils";

export interface TextareaProps extends React.TextareaHTMLAttributes<HTMLTextAreaElement> {}

const Textarea = React.forwardRef<HTMLTextAreaElement, TextareaProps>(({ className, ...props }, ref) => (
  <textarea
    ref={ref}
    className={cn(
      "flex min-h-[80px] w-full bg-transparent text-bone placeholder:italic placeholder:text-bone-dim focus-visible:outline-none disabled:cursor-not-allowed disabled:opacity-50 resize-none",
      className
    )}
    {...props}
  />
));
Textarea.displayName = "Textarea";

export { Textarea };
