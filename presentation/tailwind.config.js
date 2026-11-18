/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: { extend: {
    colors: { pink: { DEFAULT: '#E5197E', soft: '#FDE7F2', deep: '#B5115F' }, blue: { DEFAULT: '#1E3FA0', soft: '#E8EDFA', deep: '#0A1B4D' },
              ink: '#121530', mute: '#5B6079', line: '#E6E8F0' },
    fontFamily: { head: ['Poppins', 'Avenir Next', 'system-ui', 'sans-serif'], sans: ['Inter', 'system-ui', '-apple-system', 'Segoe UI', 'sans-serif'] } } },
  plugins: [],
}
