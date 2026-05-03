import type { Config } from 'tailwindcss';

const config: Config = {
  content: ['./src/**/*.{js,ts,jsx,tsx,mdx}'],
  theme: {
    extend: {
      colors: {
        // Çat Kapında brand — saks mavisi
        brand: {
          DEFAULT: '#0F52BA',
          light: '#3B7BCF',
          dark: '#0A3F8F',
          soft: '#E8EFFB',
          mist: '#F2F6FC',
          border: '#C9DAF1',
        },
        cream: {
          50: '#FDFAF3',
          100: '#F8F2E6',
          200: '#F0E6D0',
          300: '#E5D4B0',
          400: '#C9AE7A',
          soft: '#FAF6EE',
          warm: '#E8D9B5',
        },
        bg: {
          DEFAULT: '#F8F5EE',
          surface: '#FFFFFF',
          surface2: '#F4EFE3',
          surface3: '#EDE5D2',
        },
        text: {
          DEFAULT: '#0B0D17',
          2: '#4D5468',
          3: '#8B92A7',
          4: '#B8BECC',
        },
        border: {
          DEFAULT: '#ECEEF3',
          strong: '#E2E5EC',
        },
      },
      fontFamily: {
        sans: ['"Inter Tight"', 'system-ui', 'sans-serif'],
        display: ['"Bricolage Grotesque"', 'system-ui', 'sans-serif'],
        mono: ['"JetBrains Mono"', 'ui-monospace', 'monospace'],
      },
      boxShadow: {
        xs: '0 1px 2px rgba(15, 23, 42, 0.04)',
        sm: '0 1px 3px rgba(15, 23, 42, 0.05), 0 1px 2px rgba(15, 23, 42, 0.03)',
        md: '0 4px 12px rgba(15, 23, 42, 0.05), 0 2px 4px rgba(15, 23, 42, 0.04)',
        lg: '0 10px 32px rgba(15, 23, 42, 0.08), 0 4px 8px rgba(15, 23, 42, 0.04)',
        xl: '0 20px 48px rgba(15, 23, 42, 0.12), 0 8px 16px rgba(15, 23, 42, 0.06)',
      },
    },
  },
  plugins: [],
};

export default config;
