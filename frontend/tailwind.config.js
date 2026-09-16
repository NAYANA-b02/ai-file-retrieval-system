/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        appBg: '#F8F7FC',
        appCard: '#FFFFFF',
        appBorder: '#E2E8F0',
        mainText: '#334155',
        secondaryText: '#64748B',
        brand: {
          50: '#FAF8FF',
          100: '#EDE9FE',
          200: '#DDD6FE',
          300: '#C4B5FD',
          400: '#A78BFA',
          500: '#8B5CF6',
          600: '#7C3AED',
          700: '#6D28D9',
        },
        lavender: {
          DEFAULT: '#A78BFA',
          light: '#EDE9FE',
          dark: '#7C3AED',
        },
        softBlue: {
          DEFAULT: '#BFDBFE',
          light: '#EFF6FF',
          dark: '#3B82F6',
        },
        mint: {
          DEFAULT: '#BBF7D0',
          light: '#F0FDF4',
          dark: '#16A34A',
        },
        peach: {
          DEFAULT: '#FED7AA',
          light: '#FFF7ED',
          dark: '#EA580C',
        },
        rose: {
          DEFAULT: '#FDA4AF',
          light: '#FFF1F2',
          dark: '#E11D48',
        },
      },
      boxShadow: {
        'subtle': '0 1px 3px 0 rgba(0, 0, 0, 0.04), 0 1px 2px -1px rgba(0, 0, 0, 0.04)',
        'card': '0 2px 8px -2px rgba(100, 116, 139, 0.08), 0 1px 4px -1px rgba(100, 116, 139, 0.04)',
        'card-hover': '0 8px 16px -4px rgba(100, 116, 139, 0.12), 0 2px 6px -2px rgba(100, 116, 139, 0.06)',
      },
    },
  },
  plugins: [],
}
