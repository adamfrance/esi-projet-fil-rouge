// medisecure-frontend/vite.config.ts
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import path from "path";

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],

  // Configuration du serveur de développement
  server: {
    host: "0.0.0.0",
    port: 3000,
    strictPort: true,
    watch: {
      usePolling: true, // Nécessaire pour Docker sur certains systèmes
    },
    hmr: {
      clientPort: 3000, // Pour le Hot Module Replacement dans Docker
    },
  },

  // Configuration pour la prévisualisation
  preview: {
    host: "0.0.0.0",
    port: 3000,
    strictPort: true,
  },

  // Résolution des chemins
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
      "@components": path.resolve(__dirname, "./src/components"),
      "@pages": path.resolve(__dirname, "./src/pages"),
      "@services": path.resolve(__dirname, "./src/services"),
      "@hooks": path.resolve(__dirname, "./src/hooks"),
      "@utils": path.resolve(__dirname, "./src/utils"),
      "@types": path.resolve(__dirname, "./src/types"),
      "@assets": path.resolve(__dirname, "./src/assets"),
    },
  },

  // Configuration de build
  build: {
    outDir: "dist",
    sourcemap: true,
    minify: "esbuild",
    target: "esnext",
    rollupOptions: {
      output: {
        manualChunks: {
          // Séparation des chunks pour optimiser le chargement
          vendor: ["react", "react-dom"],
          router: ["react-router-dom"],
          forms: ["react-hook-form", "@hookform/resolvers", "zod"],
          ui: ["@headlessui/react", "react-hot-toast"],
          state: ["@reduxjs/toolkit", "react-redux"],
          http: ["axios"],
        },
      },
    },
  },

  // Configuration pour les tests
  test: {
    globals: true,
    environment: "jsdom",
    setupFiles: ["./src/test/setup.ts"],
    css: true,
  },

  // Variables d'environnement
  define: {
    __APP_VERSION__: JSON.stringify(process.env.npm_package_version),
  },

  // Configuration CSS
  css: {
    devSourcemap: true,
    postcss: "./postcss.config.js",
  },
});
