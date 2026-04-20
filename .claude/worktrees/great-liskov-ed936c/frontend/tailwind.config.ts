import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}",
    "./lib/**/*.{ts,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // brand palette updated to terracotta/sienna — matches --accent
        brand: {
          50:  "#FFF7ED",
          100: "#FFEDD5",
          200: "#FED7AA",
          300: "#FDBA74",
          400: "#FB923C",
          500: "#EA580C",
          600: "#C2410C",   // primary accent
          700: "#9A3412",
          800: "#7C2D12",
          900: "#431407",
        },
        // explicit accent alias (same root, convenient naming)
        accent: {
          DEFAULT: "#C2410C",
          light:   "#FED7AA",
          hover:   "#9A3412",
        },
        // warm neutral scale — body, backgrounds, borders
        warm: {
          50:  "#FAF9F6",   // --bg-primary
          100: "#F3F1ED",   // --bg-secondary
          200: "#E7E5E0",   // --border
          300: "#D4D0C8",   // --border-strong
          400: "#A8A29E",   // --text-muted
          500: "#78716C",   // --text-secondary
          900: "#1C1917",   // --text-primary
        },
        // canvas dark theme
        canvas: {
          DEFAULT: "#0D0D14",
          node:    "#FFFFFF",
          subtle:  "#1A1A26",
          border:  "rgba(255,255,255,0.08)",
        },
        // semantic
        success: "#15803D",
        warning: "#B45309",
      },
      fontFamily: {
        display: ['"Instrument Serif"', "Georgia", "serif"],
        sans:    ['"Plus Jakarta Sans"', "system-ui", "-apple-system", "BlinkMacSystemFont", "sans-serif"],
        mono:    ['"JetBrains Mono"', '"Fira Code"', "monospace"],
      },
      boxShadow: {
        "warm-sm": "0 1px 3px rgba(28,25,23,0.08)",
        "warm-md": "0 4px 16px rgba(28,25,23,0.10)",
        "canvas":  "0 4px 20px rgba(0,0,0,0.4)",
      },
      borderRadius: {
        node: "6px",
      },
    },
  },
  plugins: [require("@tailwindcss/forms")],
};

export default config;
