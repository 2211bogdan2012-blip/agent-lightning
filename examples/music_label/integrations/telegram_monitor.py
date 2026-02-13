#!/usr/bin/env python3
"""
telegram_monitor.py — Автоматический мониторинг AI-команды лейбла через Telegram.

Отправляет статус-апдейты в Telegram:
- При завершении фазы разработки
- По расписанию (каждый час)
- По команде /status в боте

Использование:
    # Одноразовый статус
    python telegram_monitor.py --once

    # Мониторинг с интервалом (каждые 30 мин)
    python telegram_monitor.py --interval 1800

    # Проверить конкретный репо
    python telegram_monitor.py --repo /path/to/repo --once

Переменные окружения:
    TELEGRAM_BOT_TOKEN — токен бота от BotFather
    TELEGRAM_CHAT_ID — ID чата для отправки (узнать через @userinfobot)
"""

import os
import sys
import json
import time
import subprocess
import urllib.request
import urllib.parse
from datetime import datetime


# Конфигурация — берётся из ENV или хардкод для НЕКСТ АП
BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "8556856882:AAEfODS2uV4_5DNSh1CSsT4qhMl8EDmBROw")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "202800925")
REPO_PATH = os.environ.get("LABEL_REPO_PATH", os.path.expanduser("~/nekstap-royalty-bot"))


def send_telegram(text: str, parse_mode: str = "HTML") -> bool:
    """Отправляет сообщение в Telegram через curl (обходит SSL проблемы на macOS)."""
    try:
        result = subprocess.run(
            ["curl", "-s", "-X", "POST",
             f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
             "-d", f"chat_id={CHAT_ID}",
             "-d", f"parse_mode={parse_mode}",
             "-d", f"text={text}"],
            capture_output=True, text=True, timeout=15,
        )
        return '"ok":true' in result.stdout
    except Exception as e:
        print(f"❌ Telegram send failed: {e}")
        return False


def get_git_status(repo_path: str) -> dict:
    """Собирает статус Git-репозитория."""
    def run(cmd):
        try:
            result = subprocess.run(
                cmd, capture_output=True, text=True, cwd=repo_path, timeout=10
            )
            return result.stdout.strip()
        except Exception:
            return ""
    
    commits = run(["git", "log", "--oneline", "-5"])
    branch = run(["git", "branch", "--show-current"])
    total_commits = run(["git", "rev-list", "--count", "HEAD"])
    last_commit_time = run(["git", "log", "-1", "--format=%cr"])
    
    return {
        "branch": branch,
        "total_commits": total_commits,
        "last_commit_time": last_commit_time,
        "recent_commits": commits,
    }


def get_test_status(repo_path: str) -> dict:
    """Запускает pytest и возвращает результат."""
    try:
        result = subprocess.run(
            ["python3", "-m", "pytest", "tests/", "--tb=no", "-q"],
            capture_output=True, text=True, cwd=repo_path, timeout=60,
        )
        output = result.stdout.strip()
        # Парсим "124 passed in 4.73s"
        for line in output.split("\n"):
            if "passed" in line:
                return {"status": "✅", "summary": line.strip()}
        return {"status": "⚠️", "summary": output[-100:] if output else "no output"}
    except Exception as e:
        return {"status": "❌", "summary": str(e)[:100]}


def get_phase_status(repo_path: str) -> list:
    """Проверяет маркеры фаз."""
    phases = [
        ("Phase 1: Тесты", "PHASE1_COMPLETE"),
        ("Phase 2: Auto-fetch Koala", "PHASE2_COMPLETE"),
        ("Phase 3: Контракты + команды", "PHASE3_COMPLETE"),
        ("Phase 4: Всё готово", "ALL_PHASES_COMPLETE"),
    ]
    result = []
    for name, marker in phases:
        # Проверяем и файл, и git log
        file_exists = os.path.exists(os.path.join(repo_path, marker))
        git_check = subprocess.run(
            ["git", "log", "--oneline", "--all", f"--grep={marker}"],
            capture_output=True, text=True, cwd=repo_path, timeout=5
        )
        done = file_exists or marker.lower() in git_check.stdout.lower()
        result.append({"name": name, "done": done})
    return result


def get_agent_teams_status() -> str:
    """Проверяет запущены ли Agent Teams."""
    try:
        result = subprocess.run(
            ["ps", "aux"], capture_output=True, text=True, timeout=5
        )
        claude_procs = [l for l in result.stdout.split("\n") if "claude" in l.lower() 
                        and "grep" not in l and "Claude.app" not in l and "ShipIt" not in l]
        return f"{len(claude_procs)} процессов Claude Code"
    except Exception:
        return "не удалось проверить"


def build_status_message(repo_path: str) -> str:
    """Собирает полное статусное сообщение."""
    now = datetime.now().strftime("%H:%M %d.%m.%Y")
    git = get_git_status(repo_path)
    tests = get_test_status(repo_path)
    phases = get_phase_status(repo_path)
    agents = get_agent_teams_status()
    
    # Фазы
    phase_lines = []
    for p in phases:
        icon = "✅" if p["done"] else "⏳"
        phase_lines.append(f"  {icon} {p['name']}")
    
    # Собираем сообщение
    msg = f"""<b>🎵 НЕКСТ АП — Status Update</b>
<i>{now}</i>

<b>📊 Git:</b> {git['branch']} · {git['total_commits']} коммитов
Последний: {git['last_commit_time']}

<b>🧪 Тесты:</b> {tests['status']} {tests['summary']}

<b>📦 Фазы разработки:</b>
{chr(10).join(phase_lines)}

<b>🤖 Claude Code:</b> {agents}

<b>Последние коммиты:</b>
<code>{git['recent_commits']}</code>"""
    
    return msg


def monitor_loop(repo_path: str, interval: int = 3600):
    """Основной цикл мониторинга."""
    print(f"🔄 Starting monitor (interval: {interval}s)")
    print(f"   Repo: {repo_path}")
    print(f"   Chat: {CHAT_ID}")
    
    last_commit = ""
    
    while True:
        # Проверяем есть ли новые коммиты
        current = subprocess.run(
            ["git", "log", "-1", "--format=%H"],
            capture_output=True, text=True, cwd=repo_path, timeout=5
        ).stdout.strip()
        
        if current != last_commit:
            msg = build_status_message(repo_path)
            if send_telegram(msg):
                print(f"✅ {datetime.now().strftime('%H:%M')} — Status sent to Telegram")
            last_commit = current
        else:
            print(f"⏳ {datetime.now().strftime('%H:%M')} — No changes")
        
        time.sleep(interval)


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Telegram monitor for label AI team")
    parser.add_argument("--once", action="store_true", help="Send status once and exit")
    parser.add_argument("--interval", type=int, default=3600, help="Check interval in seconds")
    parser.add_argument("--repo", default=REPO_PATH, help="Path to git repo")
    args = parser.parse_args()
    
    if args.once:
        msg = build_status_message(args.repo)
        print(msg.replace("<b>", "").replace("</b>", "").replace("<i>", "").replace("</i>", "")
              .replace("<code>", "").replace("</code>", ""))
        if send_telegram(msg):
            print("\n✅ Sent to Telegram!")
        else:
            print("\n❌ Failed to send")
    else:
        monitor_loop(args.repo, args.interval)


if __name__ == "__main__":
    main()
