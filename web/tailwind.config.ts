import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      fontFamily: { sans: ["'Inter Variable'", "system-ui", "sans-serif"] },
      colors: {
        brand: {
          50: "#eef5ff", 100: "#d9e8ff", 200: "#bcd6ff", 300: "#8ebcff", 400: "#5997ff",
          500: "#3372fb", 600: "#1d54f0", 700: "#1641d6", 800: "#1936ad", 900: "#1a3288", 950: "#152153",
        },
        accent: { 400: "#ffb547", 500: "#ff9a1f", 600: "#f07c05", 700: "#c75c08" },
        ink: { 900: "#0f172a", 700: "#334155", 500: "#64748b", 300: "#cbd5e1", 100: "#f1f5f9" },
      },
      boxShadow: {
        card: "0 1px 2px rgba(15,23,42,.04), 0 4px 16px -4px rgba(15,23,42,.08)",
        pop: "0 12px 40px -8px rgba(15,23,42,.25)",
      },
    },
  },
  plugins: [],
};
export default config;
