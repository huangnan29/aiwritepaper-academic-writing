#!/usr/bin/env bash
set -euo pipefail

# 该脚本为无 Node.js 环境提供完整目录安装，默认不会覆盖已有技能。
SKILL_NAME="aiwritepaper-agentic-skill"
REPO_URL="https://github.com/huangnan29/aiwritepaper-agentic-skill.git"

AGENT="${1:-}"
SCOPE="${2:-user}"
FORCE="${3:-}"

usage() {
  cat <<'EOF'
用法：install.sh <agent> [user|project] [--force]
agent：codex | claude | cursor | gemini | copilot | opencode | universal
示例：install.sh codex user
      install.sh cursor project --force
EOF
}

if [[ -z "$AGENT" ]] || [[ "$SCOPE" != "user" && "$SCOPE" != "project" ]]; then
  usage
  exit 2
fi

if [[ "$SCOPE" == "user" ]]; then
  case "$AGENT" in
    codex) TARGET="$HOME/.codex/skills/$SKILL_NAME" ;;
    claude) TARGET="$HOME/.claude/skills/$SKILL_NAME" ;;
    cursor) TARGET="$HOME/.cursor/skills/$SKILL_NAME" ;;
    gemini) TARGET="$HOME/.gemini/skills/$SKILL_NAME" ;;
    copilot) TARGET="$HOME/.copilot/skills/$SKILL_NAME" ;;
    opencode) TARGET="${XDG_CONFIG_HOME:-$HOME/.config}/opencode/skills/$SKILL_NAME" ;;
    universal) TARGET="$HOME/.agents/skills/$SKILL_NAME" ;;
    *) echo "不支持的 agent：$AGENT" >&2; usage; exit 2 ;;
  esac
else
  case "$AGENT" in
    codex|universal) TARGET="$PWD/.agents/skills/$SKILL_NAME" ;;
    claude) TARGET="$PWD/.claude/skills/$SKILL_NAME" ;;
    cursor) TARGET="$PWD/.cursor/skills/$SKILL_NAME" ;;
    gemini) TARGET="$PWD/.gemini/skills/$SKILL_NAME" ;;
    copilot) TARGET="$PWD/.github/skills/$SKILL_NAME" ;;
    opencode) TARGET="$PWD/.opencode/skills/$SKILL_NAME" ;;
    *) echo "不支持的 agent：$AGENT" >&2; usage; exit 2 ;;
  esac
fi

if [[ -e "$TARGET" ]]; then
  if [[ "$FORCE" != "--force" ]]; then
    echo "目标已存在，未覆盖：$TARGET" >&2
    echo "如需更新，请重新运行并添加 --force；旧目录会被备份。" >&2
    exit 1
  fi
  BACKUP="${TARGET}.backup.$(date +%Y%m%d%H%M%S)"
  mv "$TARGET" "$BACKUP"
  echo "旧版本已备份到：$BACKUP"
fi

TMP_DIR="$(mktemp -d)"
trap 'rm -rf "$TMP_DIR"' EXIT
git clone --depth 1 "$REPO_URL" "$TMP_DIR/source" >/dev/null
rm -rf "$TMP_DIR/source/.git"
mkdir -p "$(dirname "$TARGET")"
mkdir -p "$TARGET"
cp -R "$TMP_DIR/source/." "$TARGET/"

echo "安装完成：$TARGET"
echo "请在目标 agent 中刷新技能列表或重新启动会话。"
