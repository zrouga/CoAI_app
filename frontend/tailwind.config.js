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
          DEFAULT: '#0F4C81',
          50: '#E6EEF5',
          100: '#CCDCEA',
          200: '#99BAD5',
          300: '#6697C0',
          400: '#3375AB',
          500: '#0F4C81', // Primary indigo
          600: '#0D4373',
          700: '#0B3A65',
          800: '#083057',
          900: '#062749',
        },
        accent: {
          DEFAULT: '#50A5FF',
          50: '#EDF6FF',
          100: '#DBEEFF',
          200: '#B7DDFF',
          300: '#93CCFF',
          400: '#6FB7FF',
          500: '#50A5FF', // Accent blue
          600: '#1C8DFF',
          700: '#0077E6',
          800: '#0062BD',
          900: '#004C94',
        },
        background: '#F3F6FA',
      },
    },
  },
  plugins: [],
}
