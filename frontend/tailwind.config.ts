const config = {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        border: "hsl(var(--border))",
        background: "hsl(var(--background))",
        foreground: "hsl(var(--foreground))",
        muted: "hsl(var(--muted))",
        card: "hsl(var(--card))",
        accent: "hsl(var(--accent))",
        ring: "hsl(var(--ring))"
      },
      boxShadow: {
        panel: "0 16px 40px -20px rgba(18, 52, 84, 0.45)"
      }
    }
  },
  plugins: []
};

export default config;
