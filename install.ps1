param(
    [string]$Agent,
    [string]$Scope,
    [switch]$Force
)

# AIWritePaper Agentic Skill Windows PowerShell 5.1 安装器。
# 只从固定仓库克隆并复制完整 skill 目录，不执行远程脚本。

$ErrorActionPreference = 'Stop'
$RepositoryUrl = 'https://github.com/huangnan29/aiwritepaper-agentic-skill.git'
$SkillName = 'aiwritepaper-agentic-skill'
$TempRoot = $null

function Stop-Install {
    param([string]$Message)

    [Console]::Error.WriteLine(('错误：{0}' -f $Message))
    exit 1
}

function Show-Usage {
    @'
用法：
  .\install.ps1 -Agent <agent> -Scope <user|project> [-Force]

Agent 可选值：codex、claude、cursor、kimi、gemini、antigravity、copilot、opencode、workbuddy、grok、zcode、zai、deepseek、deepseek-tui、universal
Scope 可选值：user、project
-Force：目标目录已存在时，确认后覆盖
'@
}

if ([string]::IsNullOrWhiteSpace($Agent)) {
    Stop-Install '必须使用 -Agent 指定目标 agent。'
}

if ([string]::IsNullOrWhiteSpace($Scope)) {
    Stop-Install '必须使用 -Scope 指定 user 或 project。'
}

$AgentKey = $Agent.ToLowerInvariant()
$ScopeKey = $Scope.ToLowerInvariant()

switch ($AgentKey) {
    'codex' { }
    'claude' { }
    'cursor' { }
    'kimi' { }
    'gemini' { }
    'antigravity' { }
    'copilot' { }
    'opencode' { }
    'workbuddy' { }
    'grok' { }
    'zcode' { }
    'zai' { }
    'deepseek' { }
    'deepseek-tui' { }
    'universal' { }
    default {
        Stop-Install ('不支持的 agent：{0}。请使用 -Agent 指定受支持的Agent。' -f $Agent)
    }
}

if ($ScopeKey -ne 'user' -and $ScopeKey -ne 'project') {
    Stop-Install ('不支持的 scope：{0}。可选值为 user 或 project。' -f $Scope)
}

$HomePath = [Environment]::GetFolderPath('UserProfile')
if ([string]::IsNullOrWhiteSpace($HomePath)) {
    Stop-Install '无法确定用户主目录。'
}

if ([string]::IsNullOrWhiteSpace($env:KIMI_CODE_HOME)) {
    $KimiCodeHome = Join-Path $HomePath '.kimi-code'
} else {
    $KimiCodeHome = $env:KIMI_CODE_HOME
}

if ($ScopeKey -eq 'project') {
    $BasePath = (Get-Location).Path
} else {
    $BasePath = $HomePath
}

if ($ScopeKey -eq 'user') {
    switch ($AgentKey) {
        'codex' { $InstallRoot = Join-Path $BasePath '.codex\skills' }
        'claude' { $InstallRoot = Join-Path $BasePath '.claude\skills' }
        'cursor' { $InstallRoot = Join-Path $BasePath '.cursor\skills' }
        'kimi' { $InstallRoot = Join-Path $KimiCodeHome 'skills' }
        'gemini' { $InstallRoot = Join-Path $BasePath '.gemini\skills' }
        'antigravity' { $InstallRoot = Join-Path $BasePath '.gemini\config\skills' }
        'copilot' { $InstallRoot = Join-Path $BasePath '.copilot\skills' }
        'opencode' { $InstallRoot = Join-Path $BasePath '.config\opencode\skills' }
        'workbuddy' { $InstallRoot = Join-Path $BasePath '.workbuddy\skills' }
        'grok' { $InstallRoot = Join-Path $BasePath '.grok\skills' }
        'zcode' { $InstallRoot = Join-Path $BasePath '.zcode\skills' }
        'zai' { $InstallRoot = Join-Path $BasePath '.zcode\skills' }
        'deepseek' { $InstallRoot = Join-Path $BasePath '.codewhale\skills' }
        'deepseek-tui' { $InstallRoot = Join-Path $BasePath '.codewhale\skills' }
        'universal' { $InstallRoot = Join-Path $BasePath '.agents\skills' }
    }
} else {
    switch ($AgentKey) {
        'codex' { $InstallRoot = Join-Path $BasePath '.codex\skills' }
        'claude' { $InstallRoot = Join-Path $BasePath '.claude\skills' }
        'cursor' { $InstallRoot = Join-Path $BasePath '.cursor\skills' }
        'kimi' { $InstallRoot = Join-Path $BasePath '.kimi-code\skills' }
        'gemini' { $InstallRoot = Join-Path $BasePath '.gemini\skills' }
        'antigravity' { $InstallRoot = Join-Path $BasePath '.agents\skills' }
        'copilot' { $InstallRoot = Join-Path $BasePath '.github\skills' }
        'opencode' { $InstallRoot = Join-Path $BasePath '.opencode\skills' }
        'workbuddy' { $InstallRoot = Join-Path $BasePath '.workbuddy\skills' }
        'grok' { $InstallRoot = Join-Path $BasePath '.grok\skills' }
        'zcode' { $InstallRoot = Join-Path $BasePath '.zcode\skills' }
        'zai' { $InstallRoot = Join-Path $BasePath '.zcode\skills' }
        'deepseek' { $InstallRoot = Join-Path $BasePath '.codewhale\skills' }
        'deepseek-tui' { $InstallRoot = Join-Path $BasePath '.codewhale\skills' }
        'universal' { $InstallRoot = Join-Path $BasePath '.agents\skills' }
    }
}

$TargetPath = Join-Path $InstallRoot $SkillName
$TargetExists = Test-Path -LiteralPath $TargetPath

if ($TargetExists -and -not $Force) {
    Stop-Install ('目标目录已存在：{0}。确认覆盖时请添加 -Force。' -f $TargetPath)
}

if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    Stop-Install '未找到 git，请先安装 git 后重试。'
}

try {
    New-Item -ItemType Directory -Path $InstallRoot -Force | Out-Null
} catch {
    Stop-Install ('无法创建安装目录：{0}。' -f $InstallRoot)
}

try {
    $TempRoot = Join-Path ([IO.Path]::GetTempPath()) ('aiwritepaper-agentic-skill-' + [Guid]::NewGuid().ToString('N'))
    New-Item -ItemType Directory -Path $TempRoot -ErrorAction Stop | Out-Null
} catch {
    Stop-Install '无法创建临时目录。'
}

$ClonePath = Join-Path $TempRoot $SkillName

try {
    & git clone --depth 1 $RepositoryUrl $ClonePath 1>$null 2>$null
    if ($LASTEXITCODE -ne 0) {
        Stop-Install ('无法从固定仓库克隆 skill：{0}' -f $RepositoryUrl)
    }
} catch {
    Stop-Install ('无法从固定仓库克隆 skill：{0}' -f $RepositoryUrl)
}

try {
    if ($Force -and $TargetExists) {
        Remove-Item -LiteralPath $TargetPath -Recurse -Force -ErrorAction Stop
    }

    New-Item -ItemType Directory -Path $TargetPath -Force -ErrorAction Stop | Out-Null

    # 逐项复制完整目录，并用 -Force 保留隐藏文件。
    Get-ChildItem -LiteralPath $ClonePath -Force | ForEach-Object {
        Copy-Item -LiteralPath $_.FullName -Destination $TargetPath -Recurse -Force -ErrorAction Stop
    }

    # 安装结果不需要临时克隆产生的 Git 元数据，但保留所有 skill 内容。
    $InstalledGitPath = Join-Path $TargetPath '.git'
    if (Test-Path -LiteralPath $InstalledGitPath) {
        Remove-Item -LiteralPath $InstalledGitPath -Recurse -Force -ErrorAction Stop
    }
} catch {
    Stop-Install ('复制完整 skill 目录失败：{0}。' -f $TargetPath)
}

Write-Output ('安装完成：{0}' -f $TargetPath)

if ($TempRoot -and (Test-Path -LiteralPath $TempRoot)) {
    Remove-Item -LiteralPath $TempRoot -Recurse -Force -ErrorAction SilentlyContinue
}
