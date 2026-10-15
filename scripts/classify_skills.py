import os
import re
import yaml
from collections import defaultdict

skills_dir = "/home/skloxo/.openviking/data/viking/default/agent/skills"

# 20 Domain Capability Bundles
DOMAIN_RULES = {
    "quant-trading": [
        "quant", "trading", "stock", "ccxt", "binance", "okx", "crypto", "orderbook",
        "backtest", "a-share", "alpha", "broker", "finance", "portfolio", "arbitrage",
        "yfinance", "3-statement", "fund", "etf", "macro"
    ],
    "web-harvest-pro": [
        "crawl", "scrape", "spider", "playwright", "puppeteer", "selenium", "bs4",
        "beautifulsoup", "harvest", "rss", "feed", "extract-web", "html-parse", "curl", "fetch"
    ],
    "presentation-designer": [
        "ppt", "powerpoint", "slides", "presentation", "marp", "mermaid", "diagram",
        "infographic", "svg", "chart-visual", "poster", "visualize"
    ],
    "codebase-engineering": [
        "git", "github", "gitlab", "refactor", "tdd", "lint", "code-review", "ast",
        "typing", "pytest", "unit-test", "architecture", "clean-code", "adr", "seam"
    ],
    "system-fleet-ops": [
        "linux", "systemd", "wsl", "process", "gc", "bash", "powershell", "crontab",
        "hardware", "disk", "cpu", "ram", "memory-leak", "kernel", "cron", "satellite"
    ],
    "cloud-infra-ops": [
        "k8s", "kubernetes", "docker", "container", "frp", "oracle", "oci", "aliyun",
        "tencent", "aws", "gcp", "azure", "helm", "terraform", "ansible", "cloud"
    ],
    "document-governance": [
        "foxconn", "doc-naming", "pdca", "daily-report", "weekly-report", "monthly-report",
        "sign-off", "report", "document", "office", "word", "excel", "xlsx", "pdf", "memo"
    ],
    "credential-vault": [
        "keepass", "vault", "password", "secret", "ssh-key", "token-rotat", "credential",
        "1password", "bitwarden", "encrypt", "decrypt", "auth-token"
    ],
    "living-asset-system": [
        "living-asset", "component-inventory", "wheel-reuse", "harvest-as-you-go", "asset-library",
        "scaffold", "boilerplate"
    ],
    "cockpit-ui": [
        "ui", "css", "tailwind", "shadcn", "react", "vite", "dark-mode", "high-density",
        "frontend", "web-ui", "cockpit", "vue", "nextjs", "component", "layout"
    ],
    "ai-harness-ops": [
        "dsh", "harness", "claude-harness", "deepseek", "qwen", "llm", "prompt",
        "context-compress", "agent-eval", "eval", "tokenshift", "wikiskill", "openclaw",
        "hermes", "cpa", "agentmail", "a2a"
    ],
    "adversarial-learning": [
        "adversarial", "first-principles", "mental-model", "reverse-engineer", "anti-fragil",
        "grill", "critique", "socratic", "munger"
    ],
    "property-cadre-ops": [
        "cadre", "apartment", "lock", "smart-lock", "dormitory", "facility", "repair",
        "meter", "energy", "tenant", "property", "hotel"
    ],
    "park-grid-governance": [
        "grid", "park", "spatial", "gis", "geofence", "patrol", "ticket", "inspect",
        "attendance", "campus"
    ],
    "network-tunnel-ops": [
        "clash", "mihomo", "tunnel", "vpn", "proxy", "ipv6", "firewall", "ttl", "cpe",
        "dns", "router", "wireguard", "v2ray", "xui"
    ],
    "database-storage-ops": [
        "sql", "database", "postgres", "sqlite", "duckdb", "redis", "mysql", "mongodb",
        "migration", "orm", "alembic", "prisma", "storage"
    ],
    "multimodal-media": [
        "ffmpeg", "image", "audio", "video", "whisper", "tts", "stt", "ocr", "mineru",
        "comfyui", "diffusion", "youtube", "media"
    ],
    "mcp-bridge-hub": [
        "mcp", "fastmcp", "tool-call", "stdio", "transport", "rpc", "bridge", "sse"
    ],
    "developer-productivity": [
        "chrome-devtools", "debug", "profile", "flamegraph", "speed", "benchmark",
        "shortcut", "terminal", "workflow", "efficiency", "search"
    ],
    "security-audit-compliance": [
        "security", "vuln", "cve", "compliance", "privacy", "mask", "quarantine",
        "permission", "iam", "rbac", "audit"
    ],
}

def classify_skill(name: str, content: str) -> str:
    name_lower = name.lower()
    content_lower = content.lower()
    
    # Priority match by domain rules
    scores = defaultdict(int)
    for bundle, keywords in DOMAIN_RULES.items():
        for kw in keywords:
            if kw in name_lower:
                scores[bundle] += 5
            if kw in content_lower:
                scores[bundle] += 1
                
    if scores:
        best_bundle = max(scores.items(), key=lambda x: x[1])[0]
        return best_bundle
    return "developer-productivity"  # Default fallback

skills = sorted([d for d in os.listdir(skills_dir) if os.path.isdir(os.path.join(skills_dir, d))])
bundle_mapping = defaultdict(list)

for s in skills:
    skill_md = os.path.join(skills_dir, s, "SKILL.md")
    content = ""
    if os.path.exists(skill_md):
        try:
            with open(skill_md, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read(2000)
        except Exception:
            pass
    bundle = classify_skill(s, content)
    bundle_mapping[bundle].append(s)

print("\n=== Skills Distribution Across 20 Capability Bundles ===")
total = 0
for b in sorted(DOMAIN_RULES.keys()):
    count = len(bundle_mapping[b])
    total += count
    print(f"  {b:30s}: {count:3d} skills")
print(f"Total mapped: {total}")
