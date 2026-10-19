import subprocess
import re
from collections import defaultdict

output = subprocess.check_output(
    ['git', 'log', '234a2d9fe..upstream/main', '--format=%h|%s'],
    text=True,
    encoding='utf-8',
    errors='replace'
)
lines = [l.strip() for l in output.splitlines() if l.strip()]

feats = []
for line in lines:
    chash, subject = line.split('|', 1)
    if re.match(r'^feat', subject, re.IGNORECASE):
        feats.append((chash, subject))

print(f"Total feat commits: {len(feats)}")

# Cluster features into logical pillars
clusters = defaultdict(list)
for chash, subj in feats:
    s = subj.lower()
    if any(k in s for k in ['gateway', 'proxy', 'reverse']):
        clusters['1. Gateway 2.0 (代理与网关)'].append((chash, subj))
    elif any(k in s for k in ['compile', 'map/shuffle', 'reduce', 'pipeline']):
        clusters['2. Knowledge Compiler (知识多阶段编译)'].append((chash, subj))
    elif any(k in s for k in ['rnfv', 'multi-write', 'transaction', 'pathlock', 'orphan']):
        clusters['3. Storage & RNFV (存储事务与锁隔离)'].append((chash, subj))
    elif any(k in s for k in ['steer', 'interrupt', 'bot', 'vikingbot']):
        clusters['4. VikingBot (流式打断/舵向/Direct执行)'].append((chash, subj))
    elif any(k in s for k in ['retrieval', 'hybrid', 'rerank', 'recall', 'search', 'aml']):
        clusters['5. Retrieval & Search (单阶段混合召回与多模态)'].append((chash, subj))
    elif any(k in s for k in ['anydoc', 'parser', 'docx', 'xlsx', 'office', 'pdf', 'tree-sitter', 'ast']):
        clusters['6. Document & AST Parsers (AnyDoc全格式与AST提取)'].append((chash, subj))
    elif any(k in s for k in ['redis', 'mysql', 'task', 'queue', 'cron']):
        clusters['7. Distributed Infra (企业级MySQL/Redis存储与外挂)'].append((chash, subj))
    elif any(k in s for k in ['studio', 'web-studio', 'chatbox', 'ui', 'theme', 'brand', 'logo']):
        clusters['8. Upstream React Studio (上游官方UI与品牌调整)'].append((chash, subj))
    elif any(k in s for k in ['plugin', 'hermes', 'opencode', 'codex', 'dsh', 'mcp', 'agent']):
        clusters['9. Agent & Client Plugins (多客户端适配器)'].append((chash, subj))
    elif any(k in s for k in ['session', 'memory', 'wm', 'context', 'extract']):
        clusters['10. Session & Memory (会话持久化与状态机)'].append((chash, subj))
    elif any(k in s for k in ['privacy', 'acl', 'auth', 'token', 'security']):
        clusters['11. Security & Privacy (ACL权限与脱敏)'].append((chash, subj))
    else:
        clusters['12. Miscellaneous (其他零散特性)'].append((chash, subj))

print("\n=== Feature Clusters Analysis ===")
for name, items in sorted(clusters.items()):
    print(f"\n📁 {name} (共 {len(items)} 个提交):")
    for chash, subj in items[:8]:
        print(f"   [{chash}] {subj}")
    if len(items) > 8:
        print(f"   ... 以及其余 {len(items)-8} 个关联提交")
