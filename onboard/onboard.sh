#!/usr/bin/env bash
# Bootstrap окружения Claude Code для разработки 1С. Идемпотентный. Org-agnostic. macOS/Linux.
# Запуск:  bash onboard/onboard.sh   [--srcdir <путь>]
set -euo pipefail
WORKDIR="$(pwd)"; SRC_DIR="${ONEC_SRC_DIR:-$HOME/erp-src}"
while [ $# -gt 0 ]; do case "$1" in
  --srcdir) SRC_DIR="$2"; shift 2;;
  --workdir) WORKDIR="$2"; shift 2;;
  *) echo "неизвестный аргумент: $1"; exit 1;;
esac; done

say(){ printf '\n== %s ==\n' "$1"; }
ok(){ printf '  [ok] %s\n' "$1"; }
warn(){ printf '  [!] %s\n' "$1"; }

TEAM_DIR="$(cd "$(dirname "$0")/.." && pwd)"
SKILLS_DST="$HOME/.claude/skills"

say "1/6 Пререквизиты"
for c in git uv java claude rg; do
  if command -v "$c" >/dev/null 2>&1; then ok "$c"; else warn "$c не найден (доустанови)"; fi
done

say "2/6 Скиллы -> ~/.claude/skills"
mkdir -p "$SKILLS_DST"
for s in 1c-dev 1c-analyst; do
  if [ -d "$TEAM_DIR/skills/$s" ]; then cp -R "$TEAM_DIR/skills/$s" "$SKILLS_DST/"; ok "скилл $s"; else warn "нет $TEAM_DIR/skills/$s"; fi
done

say "3/6 Каталог исходников 1С: $SRC_DIR"
mkdir -p "$SRC_DIR"
warn "Склонируй СВОИ репозитории конфигураций/расширений в $SRC_DIR (MCP подхватит их авто)."

say "4/6 Деплой MCP чтения кода"
cp "$TEAM_DIR/mcp/erp_mcp.py" "$SRC_DIR/erp_mcp.py"; ok "erp_mcp.py -> $SRC_DIR"

say "5/6 Профиль .mcp.json и CLAUDE.md -> $WORKDIR"
cp "$TEAM_DIR/mcp/dev.mcp.json" "$WORKDIR/.mcp.json"
cp "$TEAM_DIR/CLAUDE.md" "$WORKDIR/CLAUDE.md"; ok "профиль + правила"

say "6/6 Переменные окружения + ручные шаги"
warn "Добавь в ~/.zshrc (или ~/.bashrc): export ONEC_SRC_DIR=\"$SRC_DIR\""
cat <<EOF
[ ] Проставь версии под свою конфигурацию в CLAUDE.md.
[ ] Заполни skills/1c-dev/references/conventions-template.md под свой проект.
[ ] BSL-инструменты (если нужны): env BSL_PLATFORM_JAR / BSL_LS_MCP / BSL_JAR; ONEC_PLATFORM_PATH -> платформа 1С.
[ ] Перезапусти Claude Code в $WORKDIR -> подтверди MCP.
[ ] Self-test: спроси erp-1c (find_object) — ответ по коду из $SRC_DIR.
EOF
