module.exports = {
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        background: "var(--background)",
        foreground: "var(--foreground)",
        card: "var(--card-bg)",
        border: "var(--card-border)",
        accent: {
          blue: "var(--accent-blue)",
          purple: "var(--accent-purple)",
          green: "var(--accent-green)",
          red: "var(--accent-red)",
        },
      },
    },
  },
  plugins: [],
};
