/// <reference types="vite/client" />

// 由 vite.config.ts define 注入，来源于 package.json version 字段
// 使用时直接写 __APP_VERSION__ 即可，无需手动同步版本号
declare const __APP_VERSION__: string
