/**
 * OpenViking Satellite Plugin for Xiaomi MiMo Desktop (Windows / 3070 / 2080Ti).
 * Official ESM plugin compatible with MiMo Desktop PluginLoader (no Bun.build dependency).
 *
 * Capabilities:
 * 1. session.userQuery.pre: Prefetches relevant OpenViking memories based on user prompt.
 * 2. experimental.chat.system.transform: Injects prefetched memories directly into system prompt.
 * 3. session.post: Automatically archives long assistant messages to VK staging.
 */
import { spawn } from "node:child_process";

const PYTHON_PATH = "C:\\Users\\Skl\\.venv-openviking\\Scripts\\python.exe";
const PRE_INVOCATION_SCRIPT = "C:\\Users\\Skl\\.openviking\\ov_pre_invocation.py";
const ARCHIVER_SCRIPT = "C:\\Users\\Skl\\.openviking\\ov_stop_archiver.py";

const STEP_WORDS = new Set([
  "continue", "ok", "g", "go", "y", "n", "yes", "no",
  "好的", "继续", "收到", "?", "？", ".", "。", ",", "，", "!", "！"
]);

const memoryCache = new Map();
const sessionMemory = new Map();
const CACHE_TTL_MS = 120_000;

function runPython(script, payload, timeoutMs) {
  return new Promise((resolve) => {
    let settled = false;
    const finish = (val) => {
      if (!settled) {
        settled = true;
        resolve(val);
      }
    };
    try {
      const child = spawn(PYTHON_PATH, [script], {
        windowsHide: true,
        stdio: ["pipe", "pipe", "ignore"],
      });
      const timer = setTimeout(() => {
        try { child.kill(); } catch (_) {}
        finish("");
      }, timeoutMs);
      let out = "";
      child.stdout.on("data", (chunk) => {
        out += String(chunk);
      });
      child.on("error", () => {
        clearTimeout(timer);
        finish("");
      });
      child.on("close", () => {
        clearTimeout(timer);
        finish(out.trim());
      });
      child.stdin.write(JSON.stringify(payload));
      child.stdin.end();
    } catch (_) {
      finish("");
    }
  });
}

function isStepWord(text) {
  const s = text.trim().toLowerCase();
  if (s.length < 2) return true;
  return STEP_WORDS.has(s);
}

function pruneCache() {
  if (memoryCache.size <= 64) return;
  const now = Date.now();
  for (const [k, v] of memoryCache) {
    if (now - v.ts > CACHE_TTL_MS) memoryCache.delete(k);
  }
}

function extractAssistantText(trajectory) {
  if (!Array.isArray(trajectory)) return "";
  for (let i = trajectory.length - 1; i >= 0; i--) {
    const item = trajectory[i];
    const info = item?.info ?? item;
    const role = info?.role ?? item?.role;
    if (role !== "assistant") continue;
    const parts = item?.parts ?? info?.parts ?? [];
    const texts = [];
    for (const part of parts) {
      if (typeof part?.text === "string" && part.text.trim()) texts.push(part.text);
    }
    if (texts.length) return texts.join("\n").trim();
    if (typeof info?.content === "string" && info.content.trim()) return info.content.trim();
  }
  return "";
}

export default {
  id: "openviking",
  server: async (_input) => {
    return {
      "session.userQuery.pre": async (input, _output) => {
        const query = String(input?.query ?? "").trim();
        if (!query || isStepWord(query)) return;
        const sessionID = input?.sessionID || "default";
        const key = `${sessionID}::${query.slice(0, 256)}`;
        const cached = memoryCache.get(key);
        if (cached && Date.now() - cached.ts < CACHE_TTL_MS) {
          sessionMemory.set(sessionID, cached.text);
          return;
        }
        const mem = await runPython(PRE_INVOCATION_SCRIPT, { prompt: query }, 3500);
        if (mem && mem.includes("OpenViking")) {
          memoryCache.set(key, { text: mem, ts: Date.now() });
          sessionMemory.set(sessionID, mem);
          pruneCache();
        }
      },

      "experimental.chat.system.transform": async (input, output) => {
        const sessionID = input?.sessionID || "default";
        let mem = sessionMemory.get(sessionID) || "";
        if (!mem && memoryCache.size > 0) {
          for (const entry of memoryCache.values()) {
            if (Date.now() - entry.ts < CACHE_TTL_MS) {
              mem = entry.text;
              break;
            }
          }
        }
        if (mem && mem.includes("OpenViking")) {
          if (Array.isArray(output.system)) {
            output.system.push(mem);
          }
        }
      },

      "session.post": async (input, _output) => {
        let content = String(input?.finalText ?? "").trim();
        if (!content) {
          content = extractAssistantText(input?.trajectory || []);
        }
        if (!content || content.length < 80) return;
        void runPython(
          ARCHIVER_SCRIPT,
          { last_assistant_message: content },
          3500
        );
      },
    };
  },
};
