#!/bin/sh

# AIWritePaper Agentic Skill POSIX 安装器。
# 只从固定仓库克隆并复制完整 skill 目录，不执行远程脚本。

set -eu

REPOSITORY_URL='https://github.com/huangnan29/aiwritepaper-agentic-skill.git'
SKILL_NAME='aiwritepaper-agentic-skill'
AGENT=''
SCOPE=''
FORCE=0
TEMP_ROOT=''

print_usage() {
    cat <<'EOF'
用法：
  ./install.sh --agent <agent> --scope <user|project> [--force]

agent 可选值：codex、claude、cursor、gemini、antigravity、copilot、opencode、workbuddy、grok、universal
scope 可选值：user、project
--force：目标目录已存在时，确认后覆盖
EOF
}

fail() {
    printf '%s\n' "错误：$1" >&2
    exit 1
}

cleanup() {
    if [ -n "$TEMP_ROOT" ] && [ -d "$TEMP_ROOT" ]; then
        rm -rf "$TEMP_ROOT"
    fi
}

trap cleanup 0 1 2 15

while [ "$#" -gt 0 ]; do
    case "$1" in
        --agent)
            [ "$#" -ge 2 ] || fail '--agent 缺少参数。'
            AGENT=$2
            shift 2
            ;;
        --scope)
            [ "$#" -ge 2 ] || fail '--scope 缺少参数。'
            SCOPE=$2
            shift 2
            ;;
        --force)
            FORCE=1
            shift
            ;;
        -h|--help)
            print_usage
            exit 0
            ;;
        *)
            fail "未知参数：$1。请使用 --help 查看用法。"
            ;;
    esac
done

[ -n "$AGENT" ] || fail '必须使用 --agent 指定目标 agent。'
[ -n "$SCOPE" ] || fail '必须使用 --scope 指定 user 或 project。'

case "$AGENT" in
    codex|claude|cursor|gemini|antigravity|copilot|opencode|workbuddy|grok|universal) ;;
    *) fail "不支持的 agent：${AGENT}。可选值为 codex、claude、cursor、gemini、antigravity、copilot、opencode、workbuddy、grok、universal。" ;;
esac

case "$SCOPE" in
    user|project) ;;
    *) fail "不支持的 scope：${SCOPE}。可选值为 user 或 project。" ;;
esac

HOME_DIR=${HOME:-}
[ -n "$HOME_DIR" ] || fail '无法确定用户主目录。'

if [ "$SCOPE" = 'project' ]; then
    BASE_DIR=$(pwd -P) || fail '无法确定当前项目目录。'
else
    BASE_DIR=$HOME_DIR
fi

case "$AGENT:$SCOPE" in
    codex:project) INSTALL_ROOT="$BASE_DIR/.codex/skills" ;;
    codex:user) INSTALL_ROOT="$BASE_DIR/.codex/skills" ;;
    claude:project) INSTALL_ROOT="$BASE_DIR/.claude/skills" ;;
    claude:user) INSTALL_ROOT="$BASE_DIR/.claude/skills" ;;
    cursor:project) INSTALL_ROOT="$BASE_DIR/.cursor/skills" ;;
    cursor:user) INSTALL_ROOT="$BASE_DIR/.cursor/skills" ;;
    gemini:project) INSTALL_ROOT="$BASE_DIR/.gemini/skills" ;;
    gemini:user) INSTALL_ROOT="$BASE_DIR/.gemini/skills" ;;
    antigravity:project) INSTALL_ROOT="$BASE_DIR/.agents/skills" ;;
    antigravity:user) INSTALL_ROOT="$BASE_DIR/.gemini/config/skills" ;;
    copilot:project) INSTALL_ROOT="$BASE_DIR/.github/skills" ;;
    copilot:user) INSTALL_ROOT="$BASE_DIR/.copilot/skills" ;;
    opencode:project) INSTALL_ROOT="$BASE_DIR/.opencode/skills" ;;
    opencode:user) INSTALL_ROOT="$BASE_DIR/.config/opencode/skills" ;;
    workbuddy:project) INSTALL_ROOT="$BASE_DIR/.workbuddy/skills" ;;
    workbuddy:user) INSTALL_ROOT="$BASE_DIR/.workbuddy/skills" ;;
    grok:project) INSTALL_ROOT="$BASE_DIR/.grok/skills" ;;
    grok:user) INSTALL_ROOT="$BASE_DIR/.grok/skills" ;;
    universal:project) INSTALL_ROOT="$BASE_DIR/.agents/skills" ;;
    universal:user) INSTALL_ROOT="$BASE_DIR/.agents/skills" ;;
    *) fail '无法计算安装目标目录。' ;;
esac

TARGET_DIR="$INSTALL_ROOT/$SKILL_NAME"

case "$TARGET_DIR" in
    */"$SKILL_NAME") ;;
    *) fail '安装目标目录不安全，已停止。' ;;
esac

TARGET_EXISTS=0
if [ -e "$TARGET_DIR" ] || [ -L "$TARGET_DIR" ]; then
    TARGET_EXISTS=1
fi

if [ "$TARGET_EXISTS" -eq 1 ] && [ "$FORCE" -ne 1 ]; then
    fail "目标目录已存在：${TARGET_DIR}。确认覆盖时请添加 --force。"
fi

if ! command -v git >/dev/null 2>&1; then
    fail '未找到 git，请先安装 git 后重试。'
fi

if ! mkdir -p "$INSTALL_ROOT"; then
    fail "无法创建安装目录：${INSTALL_ROOT}。"
fi

if ! TEMP_ROOT=$(mktemp -d "${TMPDIR:-/tmp}/aiwritepaper-agentic-skill.XXXXXX"); then
    fail '无法创建临时目录。'
fi

CLONE_DIR="$TEMP_ROOT/$SKILL_NAME"

if ! git clone --depth 1 "$REPOSITORY_URL" "$CLONE_DIR" >/dev/null 2>&1; then
    fail "无法从固定仓库克隆 skill：$REPOSITORY_URL"
fi

if [ "$FORCE" -eq 1 ] && [ "$TARGET_EXISTS" -eq 1 ]; then
    rm -rf "$TARGET_DIR"
fi

if ! mkdir -p "$TARGET_DIR"; then
    fail "无法创建目标目录：${TARGET_DIR}。"
fi

# 复制完整目录，包括 references、agents 和隐藏文件。
if ! cp -R "$CLONE_DIR"/. "$TARGET_DIR"/; then
    fail "复制完整 skill 目录失败：${TARGET_DIR}。"
fi

# 安装结果不需要临时克隆产生的 Git 元数据，但保留所有 skill 内容。
if [ -d "$TARGET_DIR/.git" ]; then
    rm -rf "$TARGET_DIR/.git"
fi

printf '%s\n' "安装完成：$TARGET_DIR"
