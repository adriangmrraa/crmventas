/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: ['Inter', 'system-ui', '-apple-system', 'sans-serif'],
        display: ['Outfit', 'sans-serif'],
      },
      colors: {
        // Codexy Brand — Violet Neon
        primary: {
          DEFAULT: '#8F3DFF',
          hover: '#7B2FE6',
          dark: '#6B28CC',
          light: '#A65FFF',
          50: '#F3EEFF',
          100: '#E4D6FF',
          200: '#C9ADFF',
          300: '#AD85FF',
          400: '#9F5AFF',
          500: '#8F3DFF',
          600: '#7B2FE6',
          700: '#6B28CC',
          800: '#5A21B3',
          900: '#3D1680',
        },
        // Legacy alias — redirect medical → violet
        medical: {
          900: '#3D1680',
          800: '#5A21B3',
          700: '#6B28CC',
          600: '#7B2FE6',
          500: '#8F3DFF',
          400: '#9F5AFF',
          300: '#AD85FF',
          200: '#C9ADFF',
          100: '#E4D6FF',
          50: '#F3EEFF',
        },
        // Semantic colors
        success: {
          DEFAULT: '#22c55e',
          light: '#34d399',
          dark: '#16a34a',
        },
        warning: {
          DEFAULT: '#f59e0b',
          dark: '#d97706',
        },
        danger: {
          DEFAULT: '#ef4444',
          light: '#f87171',
          dark: '#dc2626',
        },
        info: {
          DEFAULT: '#8F3DFF',
          light: '#A65FFF',
          dark: '#6B28CC',
        },
      },
      boxShadow: {
        'soft': '0 2px 15px -3px rgba(0, 0, 0, 0.3), 0 10px 20px -2px rgba(0, 0, 0, 0.2)',
        'card': '0 4px 6px -1px rgba(0, 0, 0, 0.2), 0 2px 4px -1px rgba(0, 0, 0, 0.15)',
        'elevated': '0 10px 15px -3px rgba(0, 0, 0, 0.4), 0 4px 6px -2px rgba(0, 0, 0, 0.25)',
        'glow-violet': '0 0 24px -5px rgba(143, 61, 255, 0.3)',
        'glow-violet-sm': '0 0 12px -3px rgba(143, 61, 255, 0.25)',
      },
      borderRadius: {
        'sm': '0.375rem',
        'md': '0.5rem',
        'lg': '0.625rem',
        'xl': '0.875rem',
        '2xl': '1.125rem',
        '3xl': '1.5rem',
        '4xl': '2rem',
      },
      animation: {
        'fade-in': 'fadeIn 0.3s ease-out',
        'slide-in': 'slideIn 0.3s ease-out',
        'pulse-soft': 'pulseSoft 2s ease-in-out infinite',
      },
      keyframes: {
        fadeIn: {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        },
        slideIn: {
          '0%': { transform: 'translateX(100%)', opacity: '0' },
          '100%': { transform: 'translateX(0)', opacity: '1' },
        },
        pulseSoft: {
          '0%, 100%': { opacity: '1' },
          '50%': { opacity: '0.7' },
        },
      },
    },
  },
  plugins: [],
}
