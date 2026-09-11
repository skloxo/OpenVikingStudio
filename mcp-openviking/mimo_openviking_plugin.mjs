/**
 * OpenViking Satellite Plugin for Xiaomi MiMo Desktop (Fleet Standard SSOT).
 * Universal pure Node.js ESM - zero external dependencies (no Bun, no Python subprocess).
 *
 * Capabilities:
 * 1. experimental.chat.messages.transform: Injects prefetched OpenViking memories directly into the active user prompt.
 * 2. experimental.chat.system.transform: Injects memories into system prompt.
 * 3. session.userQuery.pre: Pre-query cache warm-up and inspection.
 * 4. session.post: Automatically archives long assistant messages to VK staging.
 */
import { readFileSync, appendFileSync } from "node:fs";
import { resolve } from "node:path";

const STEP_WORDS = new Set([
  "continue", "ok", "g", "go", "y", "n", "yes", "no",
  "好的", "继续", "收到", "?", "？", ".", "。", ",", "，", "!", "！"
]);

const memoryCache = new Map();
const sessionMemory = new Map();
const CACHE_TTL_MS = 120_000;

function log(msg) {
  try {
    const home = process.env.USERPROFILE || process.env.HOME || "C:\\Users\\Skl";
    const logPath = resolve(home, ".openviking", "plugin.log");
    const line = `[${new Date().toISOString()}] ${msg}\n`;
    appendFileSync(logPath, line, "utf8");
  } catch (_) {}
}

log("[INIT] OpenViking MiMo Plugin module evaluated");

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

  if (!env.api) env.api = "https://vk.tide.red";
  if (!env.key) env.key = "ZGVmYXVsdA.ZGVmYXVsdA.NmRjZTAxYTRiYWZlNDFlNTkwODRlYzQyZWJiYWQ3YTI4Y2E1NjRkZjc4Y2Q5YzAzOTFhYWQyZWU5NjkyMjgxNQ";
  if (!env.peer) env.peer = "xiaomimo@3070";
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

function extractTextFromPart(p) {
  if (!p) return "";
  if (typeof p === "string") return p;
  if (typeof p.text === "string" && p.text.trim()) return p.text.trim();
  if (typeof p.content === "string" && p.content.trim()) return p.content.trim();
  if (typeof p.value === "string" && p.value.trim()) return p.value.trim();
  return "";
}

function extractCleanQuery(parts, rawContent) {
  const candidates = [];
  if (Array.isArray(parts)) {
    for (const p of parts) {
      const s = extractTextFromPart(p);
      if (!s || s.includes("【OpenViking 核心记忆预取")) continue;
      const cleaned = s
        .replace(/<system-reminder>[\s\S]*?<\/system-reminder>/gi, "")
        .replace(/【OpenViking 核心记忆预取[\s\S]*?💡 协同契约[^\n]*/g, "")
        .trim();
      if (cleaned) candidates.push(cleaned);
    }
  }

  if (candidates.length === 0 && rawContent) {
    const raw = typeof rawContent === "string" ? rawContent : (typeof rawContent === "object" ? JSON.stringify(rawContent) : "");
    const cleaned = raw
      .replace(/<system-reminder>[\s\S]*?<\/system-reminder>/gi, "")
      .replace(/【OpenViking 核心记忆预取[\s\S]*?💡 协同契约[^\n]*/g, "")
      .trim();
    if (cleaned) candidates.push(cleaned);
  }

  return candidates.join("\n").trim();
}

async function fetchMemory(api, key, peer, query) {
  try {
    const url = `${api.replace(/\/+$/, "")}/api/v1/search/find`;
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), 5500);

    const headers = {
      "Content-Type": "application/json",
      "X-OpenViking-Actor-Peer": peer,
      "X-Caller": peer
    };
    if (key) {
      headers["Authorization"] = `Bearer ${key}`;
    }

    log(`[FETCH] querying ${url} query="${query.slice(0, 50)}..."`);
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

    if (!res.ok) {
      log(`[FETCH_FAIL] HTTP ${res.status}`);
      return "";
    }
    const json = await res.json();
    const result = json?.result;
    const items = [
      ...(result?.memories || []),
      ...(result?.resources || []),
      ...(result?.skills || [])
    ];
    if (!items.length) {
      log(`[FETCH_EMPTY] no items found`);
      return "";
    }

    const lines = [`【OpenViking 核心记忆预取 (${api})】`];
    const topItems = items.slice(0, 2);

    // 并发快速读取 L2 完整正文（本地 15ms），保证考卷指标、网络端口等数值 100% 完整展示
    const readPromises = topItems.map(async (item) => {
      const uri = item?.uri || "";
      if (!uri) return "";
      try {
        const readUrl = `${api.replace(/\/+$/, "")}/api/v1/content/read?uri=${encodeURIComponent(uri)}`;
        const r = await fetch(readUrl, { headers, signal: AbortSignal.timeout(2500) });
        if (r.ok) {
          const j = await r.json();
          const raw = typeof j.result === "string" ? j.result : (j.result?.content || j.result?.text || "");
          if (raw && raw.trim()) {
            return `- [${uri}]:\n${raw.trim().slice(0, 1800)}`;
          }
        }
      } catch (_) {}
      const fallback = (item.abstract || item.content || "").trim().slice(0, 800);
      return `- [${uri}]: ${fallback}`;
    });

    const readResults = await Promise.all(readPromises);
    for (const res of readResults) {
      if (res) lines.push(res);
    }

    lines.push("💡 协同契约：核心事实与全量参数已在上下文中，优先直接基于此推理；严禁重复发起相同的 find 盲搜。");
    const out = lines.join("\n");
    log(`[FETCH_SUCCESS] got ${items.length} items (${out.length} chars)`);
    return out;
  } catch (err) {
    log(`[FETCH_ERR] ${err?.message || err}`);
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
    log(`[ARCHIVE] written to ${uri}`);
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
    log("[SERVER] server init called");
    const cfg = resolveConfig();
    log(`[CONFIG] api=${cfg.api} peer=${cfg.peer}`);

    return {
      "session.userQuery.pre": async (input, _output) => {
        let query = String(input?.query ?? "").trim();
        query = query.replace(/<system-reminder>[\s\S]*?<\/system-reminder>/gi, "").trim();
        log(`[HOOK:userQuery.pre] query="${query.slice(0, 50)}"`);
        if (!query || isStepWord(query) || query.includes("【OpenViking 核心记忆预取")) return;

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

      "experimental.chat.messages.transform": async (_input, output) => {
        const msgs = output?.messages;
        log(`[HOOK:messages.transform] msgs=${Array.isArray(msgs) ? msgs.length : "none"}`);
        if (!Array.isArray(msgs) || msgs.length === 0) return;

        const lastUserMsg = msgs.findLast((m) => {
          const role = m?.info?.role || m?.role;
          return role === "user";
        });
        if (!lastUserMsg) {
          log("[HOOK:messages.transform] no user message found");
          return;
        }

        const info = lastUserMsg.info ?? lastUserMsg;
        const parts = Array.isArray(lastUserMsg.parts) ? lastUserMsg.parts : (Array.isArray(info.parts) ? info.parts : null);
        const rawContent = lastUserMsg.content || info.content || lastUserMsg.text || info.text || "";

        // Check if memory has already been injected into this message
        const alreadyInjected = parts
          ? parts.some((p) => typeof p?.text === "string" && p.text.includes("【OpenViking 核心记忆预取"))
          : typeof rawContent === "string" && rawContent.includes("【OpenViking 核心记忆预取");

        if (alreadyInjected) {
          log("[HOOK:messages.transform] memory already injected");
          return;
        }

        const query = extractCleanQuery(parts, rawContent);
        log(`[HOOK:messages.transform] extracted query="${query.slice(0, 60)}"`);
        if (!query || isStepWord(query)) return;

        const cacheKey = `query::${query.slice(0, 256)}`;
        const cached = memoryCache.get(cacheKey);
        let mem = "";
        if (cached && Date.now() - cached.ts < CACHE_TTL_MS) {
          mem = cached.text;
          log("[HOOK:messages.transform] memory hit cache");
        } else {
          mem = await fetchMemory(cfg.api, cfg.key, cfg.peer, query);
          if (mem && mem.includes("OpenViking")) {
            memoryCache.set(cacheKey, { text: mem, ts: Date.now() });
            pruneCache();
          }
        }

        if (mem && mem.includes("OpenViking")) {
          // Inject into the correct container (parts preferred, else content)
          if (Array.isArray(parts)) {
            parts.unshift({
              type: "text",
              text: `${mem}\n\n`
            });
            log("[HOOK:messages.transform] injected into parts unshift");
          } else if (typeof lastUserMsg.content === "string") {
            lastUserMsg.content = `${mem}\n\n${lastUserMsg.content}`;
            log("[HOOK:messages.transform] injected into lastUserMsg.content");
          } else if (typeof info.content === "string") {
            info.content = `${mem}\n\n${info.content}`;
            log("[HOOK:messages.transform] injected into info.content");
          } else {
            lastUserMsg.parts = [{ type: "text", text: `${mem}\n\n` }];
            log("[HOOK:messages.transform] created lastUserMsg.parts and injected");
          }
        }
      },

      "experimental.chat.system.transform": async (input, output) => {
        log("[HOOK:system.transform] called");
        const sessionID = input?.sessionID || "default";
        const mem = sessionMemory.get(sessionID) || "";
        // Only inject if sessionMemory matches current session; never cross-contaminate from generic cache
        if (mem && mem.includes("OpenViking") && Array.isArray(output.system)) {
          output.system.push(mem);
          log("[HOOK:system.transform] injected memory to output.system");
        }
      },

      "session.post": async (input, _output) => {
        log("[HOOK:session.post] called");
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
