import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig(({ command, mode }) => {
  const { C5_API_PORT, C5_UI_PORT } = loadEnv(mode, process.cwd(), "C5_");
  const port = (raw: string | undefined) => {
    const value = Number(raw);
    if (!Number.isInteger(value) || value < 1 || value > 65535) {
      throw new Error("C5_API_PORT ve C5_UI_PORT geçerli port numaraları olmalıdır.");
    }
    return value;
  };
  if (command === "build" && !C5_API_PORT && !C5_UI_PORT) return { plugins: [react()] };
  const target = `http://127.0.0.1:${port(C5_API_PORT)}`;
  const proxy = {
    "/api": { target, changeOrigin: true },
    "/ws/fleet": { target, changeOrigin: true, ws: true },
  };
  const local = { host: "127.0.0.1", port: port(C5_UI_PORT), strictPort: true, proxy };
  return { plugins: [react()], server: local, preview: local };
});
