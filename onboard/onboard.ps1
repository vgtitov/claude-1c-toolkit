<#
.SYNOPSIS
  Bootstrap окружения Claude Code для разработки 1С. Идемпотентный. Org-agnostic.
.EXAMPLE
  .\onboard.ps1
  .\onboard.ps1 -SrcDir C:\1c-src
#>
param(
  [string]$WorkDir = (Get-Location).Path,
  [string]$SrcDir  = $(if ($env:ONEC_SRC_DIR) { $env:ONEC_SRC_DIR } else { "$env:USERPROFILE\erp-src" })
)
$ErrorActionPreference = 'Stop'
function Say($m){ Write-Host "`n== $m ==" -ForegroundColor Cyan }
function Ok($m){ Write-Host "  [ok] $m" -ForegroundColor Green }
function Warn($m){ Write-Host "  [!] $m" -ForegroundColor Yellow }

$TeamDir   = Split-Path -Parent $PSScriptRoot
$SkillsDst = Join-Path $env:USERPROFILE '.claude\skills'

Say "1/6 Пререквизиты"
foreach ($c in 'git','uv','java','claude','rg') {
  if (Get-Command $c -ErrorAction SilentlyContinue) { Ok $c } else { Warn "$c не найден (доустанови)" }
}

Say "2/6 Скиллы -> ~/.claude/skills"
New-Item -ItemType Directory -Force -Path $SkillsDst | Out-Null
foreach ($s in '1c-dev','1c-analyst') {
  $src = Join-Path $TeamDir "skills\$s"
  if (Test-Path $src) { Copy-Item $src $SkillsDst -Recurse -Force; Ok "скилл $s" } else { Warn "нет $src" }
}

Say "3/6 Каталог исходников 1С: $SrcDir"
New-Item -ItemType Directory -Force -Path $SrcDir | Out-Null
Warn "Склонируй СВОИ репозитории конфигураций/расширений в $SrcDir (MCP подхватит их авто)."

Say "4/6 Деплой MCP чтения кода"
Copy-Item (Join-Path $TeamDir 'mcp\erp_mcp.py') (Join-Path $SrcDir 'erp_mcp.py') -Force
Ok "erp_mcp.py -> $SrcDir"

Say "5/6 Профиль .mcp.json и CLAUDE.md -> $WorkDir"
Copy-Item (Join-Path $TeamDir 'mcp\dev.mcp.json') (Join-Path $WorkDir '.mcp.json') -Force
Copy-Item (Join-Path $TeamDir 'CLAUDE.md') (Join-Path $WorkDir 'CLAUDE.md') -Force
Ok "разложены профиль и правила"

Say "6/6 Переменные окружения (User) + ручные шаги"
[Environment]::SetEnvironmentVariable('ONEC_SRC_DIR', $SrcDir, 'User'); Ok "ONEC_SRC_DIR=$SrcDir"
@"
[ ] Проставь версии под свою конфигурацию в CLAUDE.md (платформа, режим совместимости, БСП, библиотеки).
[ ] Заполни skills/1c-dev/references/conventions-template.md под свой проект (слои, префикс, точки расширения).
[ ] BSL-инструменты (если нужны): env BSL_PLATFORM_JAR / BSL_LS_MCP / BSL_JAR; ONEC_PLATFORM_PATH -> платформа 1С.
[ ] Перезапусти Claude Code в $WorkDir -> подтверди MCP-серверы.
[ ] Self-test: спроси erp-1c (find_object) — ответ по коду из $SrcDir.
"@ | Write-Host
