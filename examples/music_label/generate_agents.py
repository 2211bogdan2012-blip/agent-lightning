#!/usr/bin/env python3
"""
generate_agents.py — Генератор AI-агентов из конфигурации лейбла.

Читает label_config.yaml и создаёт:
1. SOUL.md для каждого агента (OpenClaw identity)
2. agents.json — реестр всех агентов
3. telegram_commands.txt — список команд для BotFather

Использование:
    python generate_agents.py --config label_config.yaml --output ./generated/
    python generate_agents.py --config label_config.yaml --openclaw ~/.openclaw/
"""

import argparse
import json
import os
import sys

try:
    import yaml
except ImportError:
    print("pip install pyyaml")
    sys.exit(1)

from agents import create_all_agents


def load_config(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def generate(config: dict, output_dir: str, openclaw_dir: str = None):
    """Генерирует все файлы агентов из конфигурации."""
    label_name = config.get("label", {}).get("name", "My Label")
    agents = create_all_agents(label_name, config)
    
    os.makedirs(output_dir, exist_ok=True)
    
    # 1. SOUL.md для каждого агента
    for agent in agents:
        agent_cfg = config.get("agents", {}).get(
            agent.codename.lower().replace("-", "_"), {}
        )
        if agent_cfg and not agent_cfg.get("enabled", True):
            print(f"  ⏭  {agent.name} ({agent.codename}) — disabled, skipping")
            continue
            
        # Сохраняем в output
        agent_dir = os.path.join(output_dir, agent.codename.lower())
        soul_path = agent.save_soul(agent_dir, label_name, {
            "artists_count": len(config.get("artists", [])),
        })
        print(f"  ✅ {agent.name} ({agent.codename}) → {soul_path}")
        
        # Дополнительно в OpenClaw если указан
        if openclaw_dir:
            workspace = f"workspace-{agent.name.lower()}"
            oc_dir = os.path.join(openclaw_dir, workspace)
            agent.save_soul(oc_dir, label_name)
            print(f"     → OpenClaw: {oc_dir}/SOUL.md")
    
    # 2. agents.json — полный реестр
    registry = {
        "label": label_name,
        "generated_at": __import__("datetime").datetime.now().isoformat(),
        "agents": [a.to_dict() for a in agents],
    }
    registry_path = os.path.join(output_dir, "agents.json")
    with open(registry_path, "w", encoding="utf-8") as f:
        json.dump(registry, f, ensure_ascii=False, indent=2)
    print(f"\n  📋 Registry → {registry_path}")
    
    # 3. Telegram commands для BotFather
    commands = []
    for agent in agents:
        for cmd in agent.commands:
            clean = cmd.command.split()[0].lstrip("/")
            commands.append(f"{clean} - {cmd.description}")
    
    cmds_path = os.path.join(output_dir, "telegram_commands.txt")
    with open(cmds_path, "w", encoding="utf-8") as f:
        f.write("\n".join(sorted(set(commands))))
    print(f"  🤖 BotFather commands → {cmds_path}")
    
    print(f"\n✅ Generated {len(agents)} agents for '{label_name}'")
    return agents


def main():
    parser = argparse.ArgumentParser(description="Generate AI agents for music label")
    parser.add_argument("--config", required=True, help="Path to label_config.yaml")
    parser.add_argument("--output", default="./generated", help="Output directory")
    parser.add_argument("--openclaw", default=None, help="OpenClaw base directory")
    args = parser.parse_args()
    
    print(f"🎵 Music Label AI Agent Generator")
    print(f"   Config: {args.config}")
    print(f"   Output: {args.output}\n")
    
    config = load_config(args.config)
    generate(config, args.output, args.openclaw)


if __name__ == "__main__":
    main()
