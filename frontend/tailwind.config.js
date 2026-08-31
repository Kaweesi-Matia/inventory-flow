/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      fontFamily: {
        sans: ['"Plus Jakarta Sans"', "ui-sans-serif", "system-ui", "sans-serif"],
      },
      colors: {
        ink: {
          950: "#071018",
          900: "#0c1424",
          800: "#141e32",
          700: "#1c2940",
        },
        brand: {
          50: "#edfdf9",
          100: "#d2f7ee",
          200: "#a8eee0",
          400: "#2dd4bf",
          500: "#14b8a6",
          600: "#0f766e",
          700: "#115e59",
        },
      },
      boxShadow: {
        card: "0 1px 2px rgb(15 23 42 / 0.04), 0 12px 32px rgb(15 23 42 / 0.06)",
        glow: "0 10px 40px rgb(20 184 166 / 0.25)",
      },
    },
  },
  plugins: [],
};
