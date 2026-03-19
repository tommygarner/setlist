/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        brand: '#1DB954',
        surface: '#1A1F2E',
        base: '#0E1117',
        muted: '#6B7280',
      },
    },
  },
  plugins: [],
}
