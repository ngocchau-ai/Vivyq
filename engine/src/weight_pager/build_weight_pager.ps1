# build_weight_pager.ps1 — Build cautreo_pager.dll using LLVM-MinGW GCC
#
# Usage: .\build_weight_pager.ps1 [-Test]

param(
    [switch]$Test
)

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$BinDir = Join-Path $ScriptDir "..\..\bin"
$SrcDir = $ScriptDir

Write-Host "=== Cautreo Weight Pager Build ===" -ForegroundColor Cyan

# Locate GCC
$gcc = Get-Command gcc -ErrorAction SilentlyContinue
if (-not $gcc) {
    Write-Error "gcc not found. Install LLVM-MinGW and add to PATH."
    exit 1
}
Write-Host "Compiler: $($gcc.Source)" -ForegroundColor Green

# Ensure bin directory exists
if (-not (Test-Path $BinDir)) {
    New-Item -ItemType Directory -Force -Path $BinDir | Out-Null
}

$Target = Join-Path $BinDir "cautreo_pager.dll"

# Compile
Write-Host "Building $Target ..."
$Sources = @(
    (Join-Path $SrcDir "ct_gguf_reader.c"),
    (Join-Path $SrcDir "ct_weight_pager.c")
)

& gcc -shared -O2 -Wall -Wextra -DCT_PAGER_BUILD=1 `
    -o $Target `
    $Sources `
    -lm

if ($LASTEXITCODE -ne 0) {
    Write-Error "Build failed with exit code $LASTEXITCODE"
    exit 1
}

Write-Host "Built: $Target" -ForegroundColor Green

# Verify exports
Write-Host "`nExported symbols:" -ForegroundColor Yellow
$exports = & nm $Target 2>$null | Select-String "ct_weight_|ct_gguf_"
if ($exports) {
    $exports | ForEach-Object { Write-Host "  $_" }
} else {
    Write-Host "  (nm not available or no symbols found)" -ForegroundColor Gray
}

if ($Test) {
    Write-Host "`nBuilding and running C tests..." -ForegroundColor Cyan
    $TestBin = Join-Path $SrcDir "test_ct_pager.exe"
    & gcc -O2 -Wall -Wextra -DCT_PAGER_BUILD=1 `
        -o $TestBin `
        (Join-Path $SrcDir "test_ct_pager.c") `
        $Sources `
        -lm
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Test build failed"
        exit 1
    }
    & $TestBin
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Tests failed"
        exit 1
    }
    Write-Host "All C tests passed!" -ForegroundColor Green
}

Write-Host "`nDone." -ForegroundColor Cyan
