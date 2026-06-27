// @ts-check
const eslint = require("@eslint/js");
const { defineConfig } = require("eslint/config");
const tseslint = require("typescript-eslint");
const angular = require("angular-eslint");

module.exports = defineConfig([
  {
    files: ["**/*.ts"],
    extends: [
      eslint.configs.recommended,
      tseslint.configs.recommended,
      tseslint.configs.stylistic,
      angular.configs.tsRecommended,
    ],
    processor: angular.processInlineTemplates,
    rules: {
      "@angular-eslint/directive-selector": [
        "error",
        {
          type: "attribute",
          prefix: "app",
          style: "camelCase",
        },
      ],
      "@angular-eslint/component-selector": [
        "error",
        {
          type: "element",
          prefix: "app",
          style: "kebab-case",
        },
      ],
      // Deliberate project-wide conventions — the API/service layer uses `any`
      // for envelope payloads and noop callbacks. Disabled rather than churn
      // hundreds of call sites; revisit when adding strict typing.
      "@typescript-eslint/no-explicit-any": "off",
      "@typescript-eslint/no-empty-function": "off",
      "@typescript-eslint/consistent-indexed-object-style": "off",
      // Both constructor and inject() DI styles are valid in Angular 17 and the
      // codebase mixes them; surface as a warning rather than blocking CI.
      "@angular-eslint/prefer-inject": "warn",
      "@angular-eslint/no-empty-lifecycle-method": "warn",
    },
  },
  {
    files: ["**/*.html"],
    extends: [
      angular.configs.templateRecommended,
      angular.configs.templateAccessibility,
    ],
    rules: {
      // Accessibility + control-flow-migration rules are surfaced as warnings
      // (non-blocking) so they remain visible without failing CI on existing
      // templates. eqeqeq stays an error (caught the one `!=` in templates).
      "@angular-eslint/template/label-has-associated-control": "warn",
      "@angular-eslint/template/prefer-control-flow": "warn",
      "@angular-eslint/template/elements-content": "warn",
      "@angular-eslint/template/interactive-supports-focus": "warn",
      "@angular-eslint/template/click-events-have-key-events": "warn",
    },
  }
]);
