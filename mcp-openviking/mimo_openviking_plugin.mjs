/**
 * OpenViking Satellite Plugin for Xiaomi MiMo Desktop (Fleet Standard SSOT).
 * Universal pure Node.js ESM - zero external dependencies (no Bun, no Python subprocess).
 *
 * Capabilities:
 * 1. session.userQuery.pre: Asynchronously prefetches OpenViking memories using native fetch.
 * 2. experimental.chat.system.transform: Injects prefetched memories directly into system prompt.
 * 3. session.post: Automatically archives long assistant messages to VK staging.
 */
import { readFileSync } from "node:fs";
import { resolve } from "node:path";

const STEP_WORDS = new Set([
  "continue", "ok", "g", "go", "y", "n", "yes", "no",
  "好的", "继续", "收到", "?", "？", ".", "。", ",", "，", "!", "！"
]);

const memoryCache = new Map();
const sessionMemory = new Map();
const CACHE_TTL_MS = 120_000;

function resolveConfig() {
  const env = {
    api: process.env.OPENVIKING_API || "",
    key: process.env.OPENVIKING_API_KEY || "",
    peer: process.env.OPENVIKING_ACTOR_PEER || ""
  };

  if (!env.api || !env.key || !env.peer) {
    try {
      const home = process.env.USERPROFILE || process.env.HOME || "C:\\Users\\Skl";
      const configPath = resolve(home, ".config", "mimocode", "mimocode.jsonc");
      const raw = readFileSync(configPath, "utf-8");

      const matchApi = raw.match(/"OPENVIKING_API"\s*:\s*"([^"]+)"/);
      const matchKey = raw.match(/"OPENVIKING_API_KEY"\s*:\s*"([^"]+)"/);
      const matchPeer = raw.match(/"OPENVIKING_ACTOR_PEER"\s*:\s*"([^"]+)"/);

      if (!env.api && matchApi) env.api = matchApi[1];
      if (!env.key && matchKey) env.key = matchKey[1];
      if (!env.peer && matchPeer) env.peer = matchPeer[1];
    } catch (_) {}
  }

  if (!env.api) env.api = "http://127.0.0.1:1933";
  if (!env.peer) env.peer = "xiaomimo@node";
  return env;
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

async function fetchMemory(api, key, peer, query) {
  try {
    const url = `${api.replace(/\/+$/, "")}/api/v1/search/find`;
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), 3500);

    const headers = {
      "Content-Type": "application/json",
      "X-OpenViking-Actor-Peer": peer,
      "X-Caller": peer
    };
    if (key) {
      headers["Authorization"] = `Bearer ${key}`;
    }

    const res = await fetch(url, {
      method: "POST",
      headers,
      body: JSON.stringify({
        query: query.slice(0, 300),
        limit: 2,
        mode: "fast"
      }),
      signal: controller.signal
    });
    clearTimeout(timer);

    if (!res.ok) return "";
    const json = await res.json();
    const result = json?.result;
    const items = [
      ...(result?.memories || []),
      ...(result?.resources || []),
      ...(result?.skills || [])
    ];
    if (!items.length) return "";

    const lines = [`【OpenViking 核心记忆预取 (${api})】`];
    for (const item of items.slice(0, 3)) {
      const uri = item.uri || "";
      const text = (item.abstract || item.content || "").trim().slice(0, 300);
      if (uri) {
        lines.push(`- [${uri}]: ${text}`);
      }
    }
    lines.push("💡 协同契约：核心事实已在上下文中，优先直接基于此推理；若需全文请直接使用 openviking_read 传入对应 URI，严禁重复发起相同的 find 盲搜。");
    return lines.join("\n");
  } catch (_) {
    return "";
  }
}

async function archiveSession(api, key, peer, content) {
  try {
    const node = (peer.split("@")[1] || "node").replace(/[^a-zA-Z0-9_-]/g, "");
    const dateStr = new Date().toISOString().slice(0, 10);
    const hash = Math.random().toString(36).slice(2, 8);
    const uri = `viking://resources/staging/${node}_sessions/${dateStr}_${hash}.md`;

    const url = `${api.replace(/\/+$/, "")}/api/v1/content/write`;
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), 3000);

    const headers = {
      "Content-Type": "application/json",
      "X-OpenViking-Actor-Peer": peer,
      "X-Caller": peer
    };
    if (key) {
      headers["Authorization"] = `Bearer ${key}`;
    }

    await fetch(url, {
      method: "POST",
      headers,
      body: JSON.stringify({
        uri,
        content: `# Xiaomi MiMo Session Archive\n- Peer: ${peer}\n- Date: ${new Date().toISOString()}\n\n## Content\n${content.slice(0, 8000)}`
      }),
      signal: controller.signal
    });
    clearTimeout(timer);
  } catch (_) {}
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
    const cfg = resolveConfig();

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
        const mem = await fetchMemory(cfg.api, cfg.key, cfg.peer, query);
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
        void archiveSession(cfg.api, cfg.key, cfg.peer, content);
      },
    };
  },
};
