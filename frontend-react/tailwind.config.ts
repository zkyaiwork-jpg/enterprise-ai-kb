import type { Config } from 'tailwindcss'

export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        primary: '#0050cb',
        'primary-container': '#0066ff',
        'primary-fixed': '#dae1ff',
        'on-primary': '#ffffff',
        'on-surface': '#191b24',
        'on-surface-variant': '#424656',
        surface: '#faf8ff',
        'surface-container': '#ecedfa',
        'surface-container-low': '#f2f3ff',
        'surface-container-lowest': '#ffffff',
        'outline-variant': '#c2c6d8',
        error: '#ba1a1a',
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
      },
      boxShadow: {
        ambient: '0 4px 10px rgba(29, 33, 41, 0.05)',
      },
    },
  },
  plugins: [],
} satisfies Config
