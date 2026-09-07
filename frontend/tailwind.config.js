/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        brand: {
          50: '#f0f4fe',
          100: '#dde6fd',
          200: '#c3d3fc',
          300: '#9cbaf9',
          400: '#6d97f4',
          500: '#4370ec',
          600: '#2d54df',
          700: '#233fc8',
          800: '#2035a3',
          900: '#1e3081',
          950: '#141d4f',
        },
      },
    },
  },
  plugins: [],
}
