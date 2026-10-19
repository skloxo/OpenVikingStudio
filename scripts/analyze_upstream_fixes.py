import subprocess
import re
from collections import defaultdict, Counter

output = subprocess.check_output(
    ['git', 'log', '234a2d9fe..upstream/main', '--format=%h|%s'],
    text=True,
    encoding='utf-8',
    errors='replace'
)
lines = [l.strip() for l in output.splitlines() if l.strip()]

fixes = []
for line in lines:
    chash, subject = line.split('|', 1)
    if re.match(r'^fix', subject, re.IGNORECASE):
        fixes.append((chash, subject))

print(f"Total fix commits: {len(fixes)}")

# Filter out trivial fixes
noise_keywords = [
    'typo', 'wechat', 'qr code', 'readme', 'docs', 'docstring',
    'comment', 'ci', 'workflow', 'badge', 'link', 'grammar',
    'spelling', 'formatting', 'lint', 'whitespace', 'logo', 'icon'
]

critical_keywords = {
    'DEADLOCK / RACE': ['lock', 'deadlock', 'race', 'hang', 'block', 'wait', 'concurrency', 'timeout'],
    'DATA LOSS / CORRUPTION': ['corrupt', 'stale', 'overwrite', 'truncate', 'lost', 'loss', 'leak', 'dirty', 'upsert', 'snapshot'],
    'MEMORY / CPU / PERF': ['oom', 'memory', 'cpu', 'infinite', 'loop', 'leak', 'exhaust', 'stall', 'gc'],
    'CRASH / EXCEPTION': ['crash', 'panic', 'none', 'typeerror', 'keyerror', 'indexerror', 'unhandled', 'exception', 'attributeerror'],
    'STORAGE & VECTORDB': ['storage', 'vikingfs', 'agfs', 'vector', 'vectordb', 'collection', 'index', 'rnfv'],
    'SESSION & MEMORY ENGINE': ['session', 'commit', 'archive', 'history', 'message', 'extractor', 'updater', 'context'],
    'GATEWAY & NETWORKING': ['gateway', 'proxy', 'http', 'stream', 'sse', 'socket', 'disconnect', 'abort', 'header'],
    'PARSER & ENCODING': ['parser', 'encoding', 'utf-8', 'decode', 'docx', 'pdf', 'ast', 'markdown']
}

categorized = defaultdict(list)
for chash, subj in fixes:
    s = subj.lower()
    is_noise = any(nk in s for nk in noise_keywords) and not any(k in s for k in ['lock', 'crash', 'corrupt', 'leak', 'lost'])
    if is_noise:
        categorized['Trivial (文档/拼写/格式)'].append((chash, subj))
        continue

    matched = False
    for cat, kws in critical_keywords.items():
        if any(kw in s for kw in kws):
            categorized[cat].append((chash, subj))
            matched = True
            break
    if not matched:
        categorized['Other Functional Fixes'].append((chash, subj))

print("\n=== Upstream Bug Fixes Breakdown ===")
for cat, items in sorted(categorized.items(), key=lambda x: -len(x[1])):
    print(f"\n🚨 {cat} (共 {len(items)} 个):")
    for chash, subj in items[:10]:
        print(f"   [{chash}] {subj}")
    if len(items) > 10:
        print(f"   ... 以及其余 {len(items)-10} 个")
