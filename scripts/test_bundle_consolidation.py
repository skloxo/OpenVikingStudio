import os
import sys
import json
import shutil
import yaml

from openviking.service.detail_preserving_merger import (
    DetailPreservingMerger,
    RetinaDetailAuditor,
    MicroEntityExtractor,
)

skills_dir = "/home/skloxo/.openviking/data/viking/default/agent/skills"

def test_single_bundle(bundle_name: str, member_skills: list):
    print(f"\n--- Testing Consolidation for: {bundle_name} ({len(member_skills)} skills) ---")
    merger = DetailPreservingMerger()
    
    # Read member skills
    member_contents = {}
    for s in member_skills:
        skill_path = os.path.join(skills_dir, s, "SKILL.md")
        if os.path.exists(skill_path):
            with open(skill_path, "r", encoding="utf-8", errors="ignore") as f:
                member_contents[s] = f.read()
                
    if not member_contents:
        print("No skills found.")
        return

    # Choose base skill
    base_name = member_skills[0]
    accumulated_content = member_contents[base_name]
    
    provenance = {
        "bundle_name": bundle_name,
        "member_skills": member_skills,
        "members_detail": {}
    }

    for inc_name in member_skills[1:]:
        inc_content = member_contents[inc_name]
        accumulated_content, is_lossless, telemetry = merger.merge_skills(
            base_content=accumulated_content,
            incoming_content=inc_content,
            bundle_name=bundle_name,
            bundle_description=f"Unified {bundle_name} Capability Bundle",
        )
        provenance["members_detail"][inc_name] = telemetry
        print(f"Merged {inc_name} -> Lossless: {is_lossless}")

    # Final overall retina audit across all member skills
    overall_missing = []
    for s_name, s_content in member_contents.items():
        ok, missing = RetinaDetailAuditor.audit(s_content, "", accumulated_content)
        if not ok:
            overall_missing.extend([f"[{s_name}] {m}" for m in missing])
            
    print(f"Overall Retina Audit for {bundle_name}: {'PASS (100% Lossless)' if not overall_missing else f'FAIL ({len(overall_missing)} missing)'}")
    if overall_missing:
        print("Sample missing:", overall_missing[:3])
    print(f"Final Bundle size: {len(accumulated_content.splitlines())} lines")

if __name__ == "__main__":
    # Test on credential-vault (4 skills)
    cred_skills = ["1password", "keepass-vault", "keepass_mcp", "vault-secrets"]
    # Only test those that actually exist in the skills dir
    existing_skills = [s for s in os.listdir(skills_dir) if os.path.isdir(os.path.join(skills_dir, s))]
    cred_test = [s for s in existing_skills if any(k in s.lower() for k in ["keepass", "1password", "vault"])]
    print("Found credential skills:", cred_test)
    test_single_bundle("credential-vault", cred_test)
