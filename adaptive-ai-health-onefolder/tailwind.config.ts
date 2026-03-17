import type { Config } from "tailwindcss";

export default {
  content: [
    "./pages/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}",
    "./lib/**/*.{ts,tsx}"
  ],
  theme: {
    extend: {
      colors: {
        clinic: {
          bg: "#f7fbff",
          surface: "#ffffff",
          border: "#e6eef6",
          text: "#0f172a",
          muted: "#475569",
          blue: "#2b6cb0",
          blueSoft: "#e6f1ff",
          green: "#2f855a",
          greenSoft: "#e8f7ef",
          amberSoft: "#fff7e6",
          redSoft: "#ffecec"
        }
      },
      boxShadow: {
        card: "0 10px 30px rgba(15, 23, 42, 0.06)"
      }
    }
  },
  plugins: []
} satisfies Config;

