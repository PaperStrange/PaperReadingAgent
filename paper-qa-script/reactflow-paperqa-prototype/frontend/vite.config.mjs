import { defineConfig } from "vite";

// 2026-09-21 实测：在 Windows 上，编辑器/工具对 src 下文件做**原子写**时会短暂产生
// `<file>.<pid>.<uuid>.tmpdir/<file>.tmp` 之类的临时目录；Vite 的 FSWatcher 一旦 watch 到它
// 就会抛 `EBUSY: resource busy or locked` 并**整个 dev server 退出**（本轮复现两次）。
// 这里只做最小加固：把这类临时产物排除出 watch 范围；**不引入任何插件**，
// 保持既有 JSX 编译行为（经典运行时，组件需 `import React`）与构建结果不变。
export default defineConfig({
  server: {
    watch: {
      ignored: ["**/*.tmpdir", "**/*.tmpdir/**", "**/*.tmp", "**/.*.tmp"],
    },
  },
});
