import js from "@eslint/js";
import globals from "globals";

const readabilityRules = {
  "no-unused-vars": [
    "error",
    {
      argsIgnorePattern: "^_",
      varsIgnorePattern: "^_",
      caughtErrors: "none",
    },
  ],
  complexity: ["error", 12],
  "max-depth": ["error", 4],
  "max-nested-callbacks": ["error", 3],
  "no-nested-ternary": "error",
  eqeqeq: ["error", "smart"],
  "no-var": "error",
  "prefer-const": "error",
  "object-shorthand": "error",
  "prefer-template": "warn",
};

export default [
  js.configs.recommended,
  {
    files: ["static/**/*.js"],
    languageOptions: {
      ecmaVersion: 2022,
      sourceType: "module",
      globals: {
        ...globals.browser,
      },
    },
    rules: readabilityRules,
  },
  {
    files: ["static/miniapp/**/*.js"],
    rules: {
      complexity: ["error", 24],
      "max-depth": ["error", 5],
    },
  },
];
