import { defineConfig } from "@playwright/test";

const port = process.env.C5_UI_PORT;
if (!port || !process.env.C5_API_PORT) throw new Error("Set C5_UI_PORT and C5_API_PORT");
const baseURL = `http://127.0.0.1:${port}`;

export default defineConfig({
  testDir: "./tests",
  outputDir: process.env.C5_BROWSER_TEST_DIR ?? "/tmp/fleet-c5-browser-tests",
  use: { baseURL, channel: "chrome", viewport: { width: 1440, height: 900 } },
  webServer: { command: "npm run dev", url: baseURL, reuseExistingServer: true },
});
