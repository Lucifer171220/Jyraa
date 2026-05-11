/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './src/pages/**/*.{js,ts,jsx,tsx,mdx}',
    './src/components/**/*.{js,ts,jsx,tsx,mdx}',
    './src/app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        primary: {
          50: '#eff6ff',
          100: '#dbeafe',
          200: '#bfdbfe',
          300: '#93c5fd',
          400: '#60a5fa',
          500: '#3b82f6',
          600: '#2563eb',
          700: '#1d4ed8',
          800: '#1e40af',
          900: '#1e3a8a',
        },
        jira: {
          blue: '#0065FF',
          dark: '#172B4D',
          gray: '#6B778C',
          lightGray: '#DFE1E6',
          green: '#36B37E',
          yellow: '#FFAB00',
          red: '#FF5630',
          purple: '#6554C0',
        }
      },
    },
  },
  plugins: [],
}