import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./src/**/*.{js,ts,jsx,tsx,mdx}"],
  theme: {
    extend: {
      colors: {
        risk: {
          critical: "#dc2626",
          high: "#ea580c",
          medium: "#d97706",
          low: "#16a34a",
        },
      },
    },
  },
  plugins: [],
};

export default config;
