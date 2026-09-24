// Start the local service and the Vite dev server together.
import { spawn } from "node:child_process";
import { fileURLToPath } from "node:url";
import { dirname, resolve } from "node:path";

const appDir = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const env = { ...process.env, LOCALAI_TOKEN: process.env.LOCALAI_TOKEN || "devtoken" };
const children = [
  spawn("uv", ["run", "localai-service"], { cwd: resolve(appDir, "../service"), env, stdio: "inherit" }),
  spawn("npx", ["vite"], { cwd: appDir, env, stdio: "inherit" }),
];
const stop = () => children.forEach((c) => c.kill("SIGTERM"));
process.on("SIGINT", stop);
process.on("SIGTERM", stop);
children.forEach((c) => c.on("exit", stop));
