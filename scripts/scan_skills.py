import os
import json
from collections import Counter

skills_dir = "/home/skloxo/.openviking/data/viking/default/agent/skills"
skills = sorted([d for d in os.listdir(skills_dir) if os.path.isdir(os.path.join(skills_dir, d))])
print(f"Total unique skills: {len(skills)}")
print("First 20:", skills[:20])
print("Last 20:", skills[-20:])

# Prefix breakdown
prefixes = [s.split("-")[0].split("_")[0] for s in skills]
counter = Counter(prefixes)
print("\nTop 25 prefixes:")
for p, c in counter.most_common(25):
    print(f"  {p}: {c}")
