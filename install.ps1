param(
    [Parameter(Mandatory = $true)]
    [ValidateSet("codex", "claude", "cursor", "gemini", "copilot", "opencode", "universal")]
    [string]$Agent,

    [ValidateSet("user", "project")]
    [string]$Scope = "user",

    [switch]$Force
)

$ErrorActionPreference = "Stop"
$SkillName = "aiwritepaper-agentic-skill"
$RepoUrl = "https://github.com/huangnan29/aiwritepaper-agentic-skill.git"
$HomePath = [Environment]::GetFolderPath("UserProfile")

# 根据客户端和安装范围选择标准技能目录。
if ($Scope -eq "user") {
    $Target = switch ($Agent) {
        "codex" { Join-Path $HomePath ".codex/skills/$SkillName" }
        "claude" { Join-Path $HomePath ".claude/skills/$SkillName" }
        "cursor" { Join-Path $HomePath ".cursor/skills/$SkillName" }
        "gemini" { Join-Path $HomePath ".gemini/skills/$SkillName" }
        "copilot" { Join-Path $HomePath ".copilot/skills/$SkillName" }
        "opencode" { Join-Path $HomePath ".config/opencode/skills/$SkillName" }
        "universal" { Join-Path $HomePath ".agents/skills/$SkillName" }
    }
} else {
    $Root = (Get-Location).Path
    $Target = switch ($Agent) {
        "codex" { Join-Path $Root ".agents/skills/$SkillName" }
        "claude" { Join-Path $Root ".claude/skills/$SkillName" }
        "cursor" { Join-Path $Root ".cursor/skills/$SkillName" }
        "gemini" { Join-Path $Root ".gemini/skills/$SkillName" }
        "copilot" { Join-Path $Root ".github/skills/$SkillName" }
        "opencode" { Join-Path $Root ".opencode/skills/$SkillName" }
        "universal" { Join-Path $Root ".agents/skills/$SkillName" }
    }
}

if (Test-Path $Target) {
    if (-not $Force) {
        throw "目标已存在，未覆盖：$Target。需要更新时请添加 -Force，旧目录会被备份。"
    }
    $Stamp = Get-Date -Format "yyyyMMddHHmmss"
    $Backup = "$Target.backup.$Stamp"
    Move-Item -Path $Target -Destination $Backup
    Write-Host "旧版本已备份到：$Backup"
}

$TempRoot = Join-Path ([System.IO.Path]::GetTempPath()) ("aiwritepaper-skill-" + [Guid]::NewGuid())
$Source = Join-Path $TempRoot "source"

try {
    New-Item -ItemType Directory -Path $TempRoot -Force | Out-Null
    git clone --depth 1 $RepoUrl $Source | Out-Null
    Remove-Item -Recurse -Force (Join-Path $Source ".git")
    New-Item -ItemType Directory -Path (Split-Path $Target -Parent) -Force | Out-Null
    Copy-Item -Path $Source -Destination $Target -Recurse
    Write-Host "安装完成：$Target"
    Write-Host "请在目标 agent 中刷新技能列表或重新启动会话。"
} finally {
    if (Test-Path $TempRoot) {
        Remove-Item -Recurse -Force $TempRoot
    }
}
