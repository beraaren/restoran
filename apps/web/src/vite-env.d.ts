/// <reference types="vite/client" />

interface ImportMetaEnv {
  /** Backend API tabanı; tanımsızsa http://localhost:8100 kullanılır. */
  readonly VITE_API_BASE?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
