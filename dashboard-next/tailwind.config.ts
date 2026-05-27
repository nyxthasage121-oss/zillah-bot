import type { Config } from "tailwindcss";

const config: Config = {
  darkMode: ["class"],
  content: ["./src/**/*.{js,ts,jsx,tsx,mdx}"],
  theme: {
    container: { center: true, padding: "2rem", screens: { "2xl": "1440px" } },
    extend: {
      colors: {
        // Codex tokens — mirror dashboard/static/css/codex.css
        ink: { 950: "#0a0708", 900: "#120d0f", 850: "#171012", 800: "#1f1618", 700: "#2a1f22" },
        bone: { DEFAULT: "#ece4d6", muted: "#c9bfb0", dim: "#8b8275" },
        blood: { DEFAULT: "#8a2424", bright: "#b03030", deep: "#3a1418" },
        gold: { DEFAULT: "#b08a3e", bright: "#d4a94d", dim: "#7a5e29" },
        mauve: { DEFAULT: "#4a3d44", dim: "#352b30" },

        // shadcn semantic tokens — mapped onto the Codex palette so
        // every shadcn component picks up the gothic look without per-
        // component overrides.
        border: "#2a1f22",
        input: "#2a1f22",
        ring: "#b08a3e",
        background: "#0a0708",
        foreground: "#ece4d6",
        primary: { DEFAULT: "#8a2424", foreground: "#f5ede0" },
        secondary: { DEFAULT: "#1f1618", foreground: "#ece4d6" },
        destructive: { DEFAULT: "#8a2424", foreground: "#f5ede0" },
        muted: { DEFAULT: "#1f1618", foreground: "#8b8275" },
        accent: { DEFAULT: "#171012", foreground: "#b08a3e" },
        popover: { DEFAULT: "#171012", foreground: "#ece4d6" },
        card: { DEFAULT: "#171012", foreground: "#ece4d6" },
      },
      borderRadius: { lg: "2px", md: "2px", sm: "2px" },
      fontFamily: {
        display: ['"Cinzel"', "serif"],
        script: ['"Cormorant Garamond"', "serif"],
        serif: ['"EB Garamond"', "serif"],
        sans: ['"Inter"', "system-ui", "sans-serif"],
      },
      keyframes: {
        "accordion-down": { from: { height: "0" }, to: { height: "var(--radix-accordion-content-height)" } },
        "accordion-up": { from: { height: "var(--radix-accordion-content-height)" }, to: { height: "0" } },
      },
      animation: {
        "accordion-down": "accordion-down 0.2s ease-out",
        "accordion-up": "accordion-up 0.2s ease-out",
      },
    },
  },
  plugins: [require("tailwindcss-animate")],
};
export default config;
