import type { Config } from 'tailwindcss';

export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        primary: {
          50: '#edf7f5', 100: '#d0ede8', 200: '#a3dbd3', 300: '#6ec4b8',
          400: '#3ba99b', 500: '#157d70', 600: '#11655a', 700: '#0d4e45',
          800: '#0a3832', 900: '#062420',
        },
        surface: { 50: '#fcfdf9', 100: '#f6f7f3', 200: '#edf1e9', 300: '#dfe6df', 400: '#c6d3c4' },
        sidebar: { DEFAULT: '#142e2b', light: '#1d3d38', hover: '#24473f', active: '#31584d' },
        ink: '#203330',
        muted: '#677973',
        'accent-green': '#bada9e',
      },
      fontFamily: { sans: ['Inter', '-apple-system', 'BlinkMacSystemFont', 'Segoe UI', 'sans-serif'] },
      boxShadow: {
        card: '0 2px 8px rgba(32,51,48,0.06)',
        'card-hover': '0 8px 24px rgba(32,51,48,0.10)',
        glow: '0 0 20px rgba(21,125,112,0.15)',
      },
      animation: {
        'fade-in': 'fadeIn 0.4s ease-out',
        'slide-up': 'slideUp 0.4s ease-out',
        'slide-right': 'slideRight 0.3s ease-out',
        shimmer: 'shimmer 2s infinite',
      },
      keyframes: {
        fadeIn: { '0%': { opacity: '0' }, '100%': { opacity: '1' } },
        slideUp: { '0%': { opacity: '0', transform: 'translateY(12px)' }, '100%': { opacity: '1', transform: 'translateY(0)' } },
        slideRight: { '0%': { opacity: '0', transform: 'translateX(-12px)' }, '100%': { opacity: '1', transform: 'translateX(0)' } },
        shimmer: { '0%': { backgroundPosition: '-200% 0' }, '100%': { backgroundPosition: '200% 0' } },
      },
    },
  },
  plugins: [],
} satisfies Config;
