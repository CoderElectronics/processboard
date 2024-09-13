module.exports = {
  purge: ['./public/**/*.html'],
  darkMode: 'media', // or 'media' or 'class'
  theme: {
    extend: {},
  },
  variants: {
    extend: {},
  },
  plugins: [
    require("flowbite/plugin")
  ]
};
