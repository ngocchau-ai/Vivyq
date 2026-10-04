# Changelog: 2026-10-04 | Antigravity (Claude Opus 5.5) | Tao moi - build vivyqu_accq (docs/DESIGN_ACCQ_KERNELS_CPP.md). ASCII-only (PowerShell 5.1).
# Dung: powershell -File scripts/build_accq.ps1
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$Bin = Join-Path $Root "build\bin"
$Obj = Join-Path $Root "build\obj_accq"
New-Item -ItemType Directory -Force $Bin, $Obj | Out-Null
$Sources = @(Get-ChildItem (Join-Path $Root "src\accq") -Filter *.cpp | ForEach-Object { $_.FullName })
if (-not $Sources) { throw "No sources in src/accq" }
$Flags = @("-std=c++20", "-O2", "-march=native", "-DNDEBUG", "-DVIVYQU_ACCQ_EXPORTS", "-I$Root\include", "-Wall", "-Wextra", "-fcx-limited-range")  # cx-limited-range: inputs are validated finite
& clang++ -shared -static @Flags @Sources -o (Join-Path $Bin "vivyqu_accq.dll")
if ($LASTEXITCODE -ne 0) { throw "DLL build failed ($LASTEXITCODE)" }
$Objs = @()
foreach ($s in $Sources) {
    $o = Join-Path $Obj ([IO.Path]::GetFileNameWithoutExtension($s) + ".o")
    & clang++ -c @Flags $s -o $o
    if ($LASTEXITCODE -ne 0) { throw "compile failed: $s" }
    $Objs += $o
}
& llvm-ar rcs (Join-Path $Bin "libvivyqu_accq.a") @Objs
if ($LASTEXITCODE -ne 0) { throw "llvm-ar failed" }
Write-Host "Built: $Bin\vivyqu_accq.dll, libvivyqu_accq.a"
