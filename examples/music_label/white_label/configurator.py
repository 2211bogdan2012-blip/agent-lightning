#!/usr/bin/env python3
"""
Label Configurator -- generate a complete AI-powered label setup.

Usage:
    python -m white_label.configurator
    # Interactive prompts for label name, artists, distributor, etc.

    # Or programmatic usage:
    cfg = LabelConfigurator()
    cfg.config = {...}
    cfg.generate_project("/path/to/output")
"""

import os
import sys
from pathlib import Path
from typing import Optional

try:
    import yaml
except ImportError:
    yaml = None  # type: ignore[assignment]

from .exceptions import ConfigurationError


class LabelConfigurator:
    """Generate a complete project skeleton for any music label."""

    DISTRIBUTORS = ["koala_music", "distrokid", "tunecore", "cdbaby"]
    STORAGE_TYPES = ["yandex_disk", "google_drive", "dropbox", "local"]
    HOSTING_PROVIDERS = ["render", "railway", "fly_io", "vercel"]
    LANGUAGES = ["ru", "en", "es"]

    def __init__(self) -> None:
        self.config: dict = {
            "label": {
                "name": "",
                "legal_entity": "",
                "owner": "",
                "currency": "USD",
                "default_split": 0.70,
            },
            "distributor": {"name": ""},
            "artists": [],
            "telegram": {"bot_token": "", "admin_ids": [], "language": "en"},
            "database": {"type": "postgresql"},
            "hosting": {"provider": "render", "tier": "free"},
            "contracts_storage": {"type": "local", "base_path": "./contracts"},
            "agents": {
                "director": {"enabled": True, "model": "opus"},
                "royalty_manager": {"enabled": True, "model": "opus"},
                "contract_manager": {"enabled": True, "model": "opus"},
                "release_manager": {"enabled": False, "model": "sonnet"},
                "analytics": {"enabled": False, "model": "sonnet"},
                "devops": {"enabled": True, "model": "sonnet"},
            },
        }

    def interactive_setup(self) -> None:
        """Run interactive CLI wizard."""
        print("=" * 50)
        print("  Music Label AI -- Setup Wizard")
        print("=" * 50)

        self.config["label"]["name"] = self._prompt("Label name", required=True)
        self.config["label"]["legal_entity"] = self._prompt("Legal entity", default="")
        self.config["label"]["owner"] = self._prompt("Owner name", required=True)
        self.config["label"]["currency"] = self._prompt("Currency", default="USD")
        split = self._prompt("Default artist split (0.0-1.0)", default="0.70")
        self.config["label"]["default_split"] = float(split)

        dist = self._prompt_choice("Distributor", self.DISTRIBUTORS)
        self.config["distributor"]["name"] = dist

        storage = self._prompt_choice("Contract storage", self.STORAGE_TYPES)
        self.config["contracts_storage"]["type"] = storage

        hosting = self._prompt_choice("Hosting provider", self.HOSTING_PROVIDERS)
        self.config["hosting"]["provider"] = hosting

        lang = self._prompt_choice("Language", self.LANGUAGES)
        self.config["telegram"]["language"] = lang

        token = self._prompt("Telegram bot token (leave empty to skip)", default="")
        self.config["telegram"]["bot_token"] = token

        num_artists = int(self._prompt("Number of artists to add now", default="0"))
        for i in range(num_artists):
            print(f"\n--- Artist {i + 1} ---")
            name = self._prompt("Artist name", required=True)
            split_str = self._prompt(
                "Split",
                default=str(self.config["label"]["default_split"]),
            )
            self.add_artist(name, float(split_str))

        print("\nConfiguration complete!")

    def generate_project(self, output_dir: str) -> dict[str, str]:
        """Generate complete project skeleton. Returns dict of created file paths."""
        errors = self.validate_config()
        if errors:
            raise ConfigurationError(
                "Invalid configuration:\n" + "\n".join(f"  - {e}" for e in errors)
            )

        base = Path(output_dir)
        created: dict[str, str] = {}

        # label_config.yaml
        created["config"] = self._write_config(base / "label_config.yaml")

        # .env.example
        created["env"] = self._write_env_example(base / ".env.example")

        # requirements.txt
        created["requirements"] = self._write_requirements(base / "requirements.txt")

        # Dockerfile
        created["dockerfile"] = self._write_dockerfile(base / "Dockerfile")

        # docker-compose.yml
        created["compose"] = self._write_docker_compose(base / "docker-compose.yml")

        # README.md
        created["readme"] = self._write_readme(base / "README.md")

        # agents/ with SOUL.md for each enabled agent
        created["agents"] = self._write_agent_souls(base / "agents")

        return created

    def add_artist(
        self,
        name: str,
        split: float,
        koala_names: Optional[list[str]] = None,
    ) -> None:
        """Add artist to config."""
        if split < 0.0 or split > 1.0:
            raise ConfigurationError(f"Split must be between 0.0 and 1.0, got {split}")
        artist = {
            "name": name,
            "split": split,
            "koala_names": koala_names or [name],
            "contract_status": "placeholder",
        }
        self.config["artists"].append(artist)

    def remove_artist(self, name: str) -> bool:
        """Remove artist from config. Returns True if found and removed."""
        before = len(self.config["artists"])
        self.config["artists"] = [
            a for a in self.config["artists"] if a["name"] != name
        ]
        return len(self.config["artists"]) < before

    def validate_config(self) -> list[str]:
        """Validate config, return list of errors (empty if valid)."""
        errors: list[str] = []

        label = self.config.get("label", {})
        if not label.get("name"):
            errors.append("Label name is required")
        if not label.get("owner"):
            errors.append("Owner name is required")

        split = label.get("default_split", 0)
        if not (0.0 <= split <= 1.0):
            errors.append(f"Default split must be 0.0-1.0, got {split}")

        dist = self.config.get("distributor", {}).get("name", "")
        if dist and dist not in self.DISTRIBUTORS:
            errors.append(f"Unknown distributor: {dist}. Choose from: {self.DISTRIBUTORS}")

        storage = self.config.get("contracts_storage", {}).get("type", "")
        if storage and storage not in self.STORAGE_TYPES:
            errors.append(f"Unknown storage type: {storage}. Choose from: {self.STORAGE_TYPES}")

        hosting = self.config.get("hosting", {}).get("provider", "")
        if hosting and hosting not in self.HOSTING_PROVIDERS:
            errors.append(f"Unknown hosting: {hosting}. Choose from: {self.HOSTING_PROVIDERS}")

        lang = self.config.get("telegram", {}).get("language", "")
        if lang and lang not in self.LANGUAGES:
            errors.append(f"Unknown language: {lang}. Choose from: {self.LANGUAGES}")

        for i, artist in enumerate(self.config.get("artists", [])):
            if not artist.get("name"):
                errors.append(f"Artist {i} missing name")
            s = artist.get("split", 0)
            if not (0.0 <= s <= 1.0):
                errors.append(f"Artist '{artist.get('name', i)}' split must be 0.0-1.0, got {s}")

        return errors

    # --- Private helpers ---

    @staticmethod
    def _prompt(text: str, default: str = "", required: bool = False) -> str:
        suffix = f" [{default}]" if default else ""
        while True:
            value = input(f"  {text}{suffix}: ").strip() or default
            if value or not required:
                return value
            print("    This field is required.")

    @staticmethod
    def _prompt_choice(text: str, choices: list[str]) -> str:
        print(f"\n  {text}:")
        for i, c in enumerate(choices, 1):
            print(f"    {i}. {c}")
        while True:
            raw = input(f"  Choose (1-{len(choices)}): ").strip()
            try:
                idx = int(raw) - 1
                if 0 <= idx < len(choices):
                    return choices[idx]
            except ValueError:
                if raw in choices:
                    return raw
            print(f"    Please enter 1-{len(choices)}")

    def _write_config(self, path: Path) -> str:
        path.parent.mkdir(parents=True, exist_ok=True)
        if yaml is not None:
            path.write_text(
                yaml.dump(self.config, allow_unicode=True, default_flow_style=False, sort_keys=False),
                encoding="utf-8",
            )
        else:
            # Fallback: write a minimal YAML-like format
            import json

            path.write_text(json.dumps(self.config, ensure_ascii=False, indent=2), encoding="utf-8")
        return str(path)

    def _write_env_example(self, path: Path) -> str:
        path.parent.mkdir(parents=True, exist_ok=True)
        dist = self.config["distributor"]["name"]
        storage = self.config["contracts_storage"]["type"]
        lines = [
            "# Database",
            "DATABASE_URL=postgresql://user:pass@localhost:5432/label_db",
            "",
            "# Telegram",
            "TELEGRAM_BOT_TOKEN=your-bot-token",
            "TELEGRAM_ADMIN_IDS=123456789",
            "",
        ]
        if dist == "koala_music":
            lines += [
                "# Koala Music",
                "KOALA_CLIENT_ID=lp-km",
                "KOALA_REFRESH_TOKEN=your-refresh-token",
                "",
            ]
        elif dist == "distrokid":
            lines += ["# DistroKid", "DISTROKID_EMAIL=your-email", "DISTROKID_CSV_PATH=./data/", ""]
        elif dist == "tunecore":
            lines += ["# TuneCore", "TUNECORE_API_KEY=your-api-key", ""]
        elif dist == "cdbaby":
            lines += ["# CD Baby", "CDBABY_API_KEY=your-api-key", ""]

        if storage == "yandex_disk":
            lines += ["# Yandex Disk", "YANDEX_DISK_TOKEN=your-token", ""]
        elif storage == "google_drive":
            lines += ["# Google Drive", "GOOGLE_DRIVE_CREDENTIALS=./credentials.json", ""]
        elif storage == "dropbox":
            lines += ["# Dropbox", "DROPBOX_ACCESS_TOKEN=your-token", ""]

        path.write_text("\n".join(lines), encoding="utf-8")
        return str(path)

    def _write_requirements(self, path: Path) -> str:
        path.parent.mkdir(parents=True, exist_ok=True)
        deps = [
            "aiohttp>=3.9",
            "asyncpg>=0.29",
            "pyyaml>=6.0",
            "python-dotenv>=1.0",
            "fpdf2>=2.7",
            "openpyxl>=3.1",
            "matplotlib>=3.8",
            "aiogram>=3.4",
        ]
        path.write_text("\n".join(deps) + "\n", encoding="utf-8")
        return str(path)

    def _write_dockerfile(self, path: Path) -> str:
        label_name = self.config["label"]["name"]
        path.parent.mkdir(parents=True, exist_ok=True)
        content = f"""\
FROM python:3.12-slim

LABEL maintainer="{label_name} AI Team"

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8080

CMD ["python", "-m", "bot"]
"""
        path.write_text(content, encoding="utf-8")
        return str(path)

    def _write_docker_compose(self, path: Path) -> str:
        path.parent.mkdir(parents=True, exist_ok=True)
        content = """\
services:
  bot:
    build: .
    env_file: .env
    depends_on:
      - db
    ports:
      - "8080:8080"
    restart: unless-stopped

  db:
    image: postgres:16-alpine
    environment:
      POSTGRES_DB: label_db
      POSTGRES_USER: label
      POSTGRES_PASSWORD: changeme
    volumes:
      - pgdata:/var/lib/postgresql/data
    ports:
      - "5432:5432"

volumes:
  pgdata:
"""
        path.write_text(content, encoding="utf-8")
        return str(path)

    def _write_readme(self, path: Path) -> str:
        label = self.config["label"]["name"]
        path.parent.mkdir(parents=True, exist_ok=True)
        content = f"""\
# {label} -- AI-Powered Music Label

Generated by the Music Label AI white-label framework.

## Quick Start

```bash
# 1. Copy environment variables
cp .env.example .env
# Edit .env with your real credentials

# 2. Start services
docker compose up -d

# 3. Run the bot
python -m bot
```

## Project Structure

```
{label.lower().replace(' ', '_')}/
  label_config.yaml  -- Label configuration
  agents/            -- AI agent SOUL.md files
  .env.example       -- Environment variables template
  Dockerfile         -- Container build
  docker-compose.yml -- Full stack with PostgreSQL
```

## Agents

Each agent has a SOUL.md file defining its identity and capabilities.
See `agents/` directory for details.
"""
        path.write_text(content, encoding="utf-8")
        return str(path)

    def _write_agent_souls(self, agents_dir: Path) -> str:
        agents_dir.mkdir(parents=True, exist_ok=True)
        label_name = self.config["label"]["name"]
        lang = self.config.get("telegram", {}).get("language", "en")

        agent_defs = {
            "director": ("NEXUS", "AI Director", "Strategic coordination and artist communication"),
            "royalty_manager": ("Rita", "Royalty Manager", "Quarterly royalty calculations and reports"),
            "contract_manager": ("Max", "Contract Manager", "Contract lifecycle and split management"),
            "release_manager": ("Lena", "Release Manager", "Release pipeline and DSP monitoring"),
            "analytics": ("Denis", "Analytics", "Stream analysis, trends, and recommendations"),
            "devops": ("Sasha", "DevOps Engineer", "CI/CD, Docker, deployment, monitoring"),
        }

        for key, (name, role, desc) in agent_defs.items():
            agent_cfg = self.config.get("agents", {}).get(key, {})
            if not agent_cfg.get("enabled", False):
                continue

            agent_path = agents_dir / key
            agent_path.mkdir(parents=True, exist_ok=True)
            soul = f"""\
# {name} -- {role}
## {label_name}

You are {name}, the {role} of {label_name}.
Model: Claude {agent_cfg.get('model', 'sonnet').title()}.

## Responsibility
{desc}

## Rules
- Be precise with numbers and data
- Report errors to NEXUS (director)
- Stay within your area of responsibility
- Log all actions for audit
"""
            (agent_path / "SOUL.md").write_text(soul, encoding="utf-8")

        return str(agents_dir)


def main() -> None:
    """CLI entry point."""
    cfg = LabelConfigurator()
    cfg.interactive_setup()

    output = input("\n  Output directory [./generated]: ").strip() or "./generated"
    created = cfg.generate_project(output)

    print(f"\nProject generated in {output}/")
    for key, path in created.items():
        print(f"  {key}: {path}")


if __name__ == "__main__":
    main()
