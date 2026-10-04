# Changelog: 2026-10-04 | Antigravity (Claude Opus 5.5) | Tao moi - build Piggyback Host (ADR_2026-10-04); exe dat ngoai repo. File ASCII-only (PowerShell 5.1 doc UTF-8 khong BOM sai).
# Dung: powershell -File tools/piggyback_host/build.ps1  [-LlamaDir D:\models\src\llama.cpp] [-OutDir D:\models\tools\piggyback_host]
param(
    [string]$LlamaDir = "D:\models\src\llama.cpp",
    [string]$OutDir = "D:\models\tools\piggyback_host"
)
$ErrorActionPreference = "Stop"
$Root = Resolve-Path (Join-Path $PSScriptRoot "..\..")
$CoreLib = Join-Path $Root "build\bin\libvivyqu_core.a"
if (-not (Test-Path $CoreLib)) { throw "Missing $CoreLib - run scripts/build_core.ps1 first" }
foreach ($f in "build\src\libllama.a", "build\ggml\src\ggml.a", "build\ggml\src\ggml-cpu.a", "build\ggml\src\ggml-base.a") {
    if (-not (Test-Path (Join-Path $LlamaDir $f))) { throw "Missing $LlamaDir\$f - build llama.cpp first (spec 8.8/8.11)" }
}
New-Item -ItemType Directory -Force $OutDir | Out-Null
$Exe = Join-Path $OutDir "piggyback_host.exe"
# VIVYQU_EXPORTS: c_api.h uses dllexport instead of dllimport -> static link with libvivyqu_core.a
& clang++ -O2 -std=c++20 -march=native -DVIVYQU_EXPORTS -D_WIN32_WINNT=0x0A00 -DWINVER=0x0A00 `
    -I"$Root\include" -I"$LlamaDir\include" -I"$LlamaDir\ggml\include" `
    (Join-Path $PSScriptRoot "piggyback_host.cpp") $CoreLib `
    "$LlamaDir\build\src\libllama.a" "$LlamaDir\build\ggml\src\ggml.a" "$LlamaDir\build\ggml\src\ggml-cpu.a" "$LlamaDir\build\ggml\src\ggml-base.a" `
    -static -o $Exe
if ($LASTEXITCODE -ne 0) { throw "Build failed (clang++ exit $LASTEXITCODE)" }
Write-Host "Built: $Exe"
