import os
import shutil
from pathlib import Path

def migrate_one_directory():
    one_dir = Path(r"c:\Users\Skl\Desktop\One")
    work_dir = Path(r"c:\Users\Skl\Desktop\Work")
    coding_dir = Path(r"c:\Users\Skl\Desktop\coding")

    # 1. 确保 coding/.gitignore 和 coding/.geminiignore 保护 personal_vault
    for ig_name in [".gitignore", ".geminiignore"]:
        ig_path = coding_dir / ig_name
        content = ig_path.read_text(encoding="utf-8") if ig_path.exists() else ""
        if "personal_vault" not in content:
            content += "\n# Private credentials & contracts\npersonal_vault/\n"
            ig_path.write_text(content, encoding="utf-8")
            print(f"[PROTECT] Added personal_vault/ to {ig_path}")

    # 2. 定义迁移计划 (源相对路径 -> 目标绝对路径)
    # Part A: 迁移至 Work
    work_app_dir = work_dir / "07_技术运维" / "03_小程序资产"
    work_app_dir.mkdir(parents=True, exist_ok=True)

    work_files = [
        "小程序注销打款验证.md",
        "富圈圈商户端注销打款验证.png",
        "富圈圈小程序注销打款验证.png",
        "富圈圈配送端小程序注销打款验证.png",
        "技术工用工小程序注销打款验证.png",
        "Pasted image 20260813154338.png",
        "Pasted image 20260813155139.png",
    ]

    for fname in work_files:
        src = one_dir / fname
        if src.exists():
            dst = work_app_dir / fname
            shutil.move(str(src), str(dst))
            print(f"[MOVE -> Work] {fname} -> {dst}")

    # Part B: 迁移至 coding
    # B1: SUB 目录
    sub_src = one_dir / "SUB"
    sub_dst = coding_dir / "SUB"
    if sub_src.exists():
        if sub_dst.exists():
            print(f"[WARN] {sub_dst} already exists, merging...")
            for item in sub_src.iterdir():
                d_item = sub_dst / item.name
                if not d_item.exists():
                    shutil.move(str(item), str(d_item))
            shutil.rmtree(str(sub_src))
        else:
            shutil.move(str(sub_src), str(sub_dst))
        print(f"[MOVE -> coding] SUB/ -> {sub_dst}")

    # B2: AI技术与体外大脑
    ai_src = one_dir / "AI技术与体外大脑"
    ai_dst = coding_dir / "OpenVikingStudio" / "docs" / "guides"
    ai_dst.mkdir(parents=True, exist_ok=True)
    if ai_src.exists():
        for item in ai_src.iterdir():
            shutil.move(str(item), str(ai_dst / item.name))
            print(f"[MOVE -> coding] {item.name} -> {ai_dst}")
        shutil.rmtree(str(ai_src))

    # B3: 对账.xlsx (个人证券账户)
    tide_docs = coding_dir / "TideTrading" / "docs"
    tide_docs.mkdir(parents=True, exist_ok=True)
    acc_src = one_dir / "对账.xlsx"
    if acc_src.exists():
        shutil.move(str(acc_src), str(tide_docs / "证券交易资金对账_2026.xlsx"))
        print(f"[MOVE -> coding] 对账.xlsx -> {tide_docs / '证券交易资金对账_2026.xlsx'}")

    # B4: VPS手册与厂商总表及备份
    vps_dst = coding_dir / "docs" / "vps_manuals"
    vps_dst.mkdir(parents=True, exist_ok=True)
    vps_files = ["海外机房VPS注册操作手册.md", "VPS厂商总表.xlsx"]
    for vf in vps_files:
        src = one_dir / vf
        if src.exists():
            shutil.move(str(src), str(vps_dst / vf))
            print(f"[MOVE -> coding] {vf} -> {vps_dst}")

    for bk in one_dir.glob(".backup_*"):
        shutil.move(str(bk), str(vps_dst / bk.name))
        print(f"[MOVE -> coding] {bk.name} -> {vps_dst}")

    # B5: 硬件配置与装机指南
    hw_src = one_dir / "硬件配置与装机指南"
    hw_dst = coding_dir / "docs" / "hardware_guides"
    if hw_src.exists():
        if hw_dst.exists():
            for item in hw_src.iterdir():
                shutil.move(str(item), str(hw_dst / item.name))
            shutil.rmtree(str(hw_src))
        else:
            shutil.move(str(hw_src), str(hw_dst))
        print(f"[MOVE -> coding] 硬件配置与装机指南/ -> {hw_dst}")

    # B6: 视觉设计、模型评估与提示词
    design_dst = coding_dir / "docs" / "design_systems"
    design_dst.mkdir(parents=True, exist_ok=True)
    if (one_dir / "MonkeyCode_暗色主题视觉规范与设计系统指南.md").exists():
        shutil.move(str(one_dir / "MonkeyCode_暗色主题视觉规范与设计系统指南.md"), str(design_dst / "MonkeyCode_暗色主题视觉规范与设计系统指南.md"))
        print("[MOVE -> coding] MonkeyCode视觉规范")

    models_dst = coding_dir / "docs" / "model_evaluations"
    models_dst.mkdir(parents=True, exist_ok=True)
    for mf in ["NIM模型评估.xlsx", "英伟达模型.xlsx"]:
        src = one_dir / mf
        if src.exists():
            shutil.move(str(src), str(models_dst / mf))
            print(f"[MOVE -> coding] {mf} -> {models_dst}")

    prompt_dst = coding_dir / "docs" / "prompts"
    prompt_dst.mkdir(parents=True, exist_ok=True)
    if (one_dir / "生图提示词").exists():
        shutil.move(str(one_dir / "生图提示词"), str(prompt_dst / "生图提示词.md"))
        print("[MOVE -> coding] 生图提示词")

    if (one_dir / "mimo-ultra").exists():
        shutil.move(str(one_dir / "mimo-ultra"), str(prompt_dst / "mimo-ultra"))
        print("[MOVE -> coding] mimo-ultra")

    # B7: 脚本 scripts
    scripts_src = one_dir / "scripts"
    scripts_dst = coding_dir / "scripts"
    scripts_dst.mkdir(parents=True, exist_ok=True)
    if scripts_src.exists():
        for item in scripts_src.iterdir():
            target_f = scripts_dst / item.name
            if not target_f.exists():
                shutil.move(str(item), str(target_f))
                print(f"[MOVE -> coding] script: {item.name}")
        shutil.rmtree(str(scripts_src))

    # B8: 个人私有安全保险库 personal_vault
    vault_dst = coding_dir / "personal_vault"
    vault_dst.mkdir(parents=True, exist_ok=True)
    vault_files = [
        "5999丽江站黄倩合同.pdf",
        "全国互联网安全管理服务平台_自评估报告_2026-07-09 20_48_25.pdf",
        "全国互联网安全管理服务平台_自评估报告_2026-07-09 20_49_43.pdf",
        "域名证书tide.beer.png",
        "账号备份antigravity_accounts_2026-07-13.json",
    ]
    for vf in vault_files:
        src = one_dir / vf
        if src.exists():
            shutil.move(str(src), str(vault_dst / vf))
            print(f"[MOVE -> personal_vault] {vf}")

    # Part C: 清理临时垃圾与退役 One 文件夹
    log_file = one_dir / "SquirrelSetup.log"
    if log_file.exists():
        log_file.unlink()
        print("[CLEANUP] SquirrelSetup.log removed")

    ini_file = one_dir / "desktop.ini"
    if ini_file.exists():
        try:
            ini_file.unlink()
            print("[CLEANUP] desktop.ini removed")
        except Exception:
            pass

    # 清理 .agents 目录（workflows 已在 coding 和 Work 备份）
    agents_dir = one_dir / ".agents"
    if agents_dir.exists():
        shutil.rmtree(str(agents_dir))
        print("[CLEANUP] One/.agents removed")

    # 检查 One 剩余内容
    remaining = list(one_dir.iterdir())
    print(f"\n[AUDIT] Remaining items in One: {len(remaining)}")
    for r in remaining:
        print(f"  - {r.name}")

    if len(remaining) == 0:
        try:
            one_dir.rmdir()
            print("\n[SUCCESS] One 目录已完美清空并彻底退役！")
        except Exception as e:
            print(f"[WARN] 移除 One 目录失败: {e}")

if __name__ == "__main__":
    migrate_one_directory()
