# VivyQu Core Build & Test Script (PowerShell)
# ===========================================
param (
    [string]$Config = "Release",
    [switch]$RunBenchmark = $false
)

$ErrorActionPreference = "Stop"

$RootDir = Split-Path -Parent $PSScriptRoot
$BuildDir = Join-Path $RootDir "build"
$BinDir = Join-Path $BuildDir "bin"

New-Item -ItemType Directory -Force -Path $BinDir | Out-Null

$ClangPath = (Get-Command clang++.exe -ErrorAction SilentlyContinue).Source
if (-not $ClangPath) {
    Write-Error "clang++.exe not found in PATH!"
}

Write-Host "=========================================================" -ForegroundColor Cyan
Write-Host "       VIVYQU CORE C++20 COMPILATION PIPELINE            " -ForegroundColor Cyan
Write-Host "=========================================================" -ForegroundColor Cyan
Write-Host "Compiler: $ClangPath"
Write-Host "Config  : $Config"

$Flags = @(
    "-std=c++20",
    "-I$RootDir/include",
    "-march=native",
    "-mavx2",
    "-mfma",
    "-mbmi",
    "-mbmi2",
    "-DVIVYQU_EXPORTS"
)

if ($Config -eq "Release") {
    $Flags += @("-O3", "-DNDEBUG")
} else {
    $Flags += @("-O0", "-g", "-DDEBUG")
}

$Sources = @(
    "$RootDir/src/core/clifford_cl12.cpp",
    "$RootDir/src/core/rotor_spin12.cpp",
    "$RootDir/src/core/hamiltonian_flow.cpp",
    "$RootDir/src/core/collapse.cpp",
    "$RootDir/src/core/geometric_scorer.cpp",
    "$RootDir/src/core/qubit_polarization.cpp",
    "$RootDir/src/core/c_api.cpp"
)

# 1. Compile Shared Library (DLL) for C-ABI / IPC
Write-Host "`n[1/3] Building Shared Library (vivyqu_core.dll)..." -ForegroundColor Yellow
$DllTarget = Join-Path $BinDir "vivyqu_core.dll"
& clang++ -shared -static -fPIC @Flags @Sources -o $DllTarget
Write-Host "      Built: $DllTarget" -ForegroundColor Green

# Đồng bộ bản DLL mà SDK Python đóng gói (pyproject package-data *.dll)
$PkgDll = Join-Path $RootDir "python\vivyqu\vivyqu_core.dll"
Copy-Item -LiteralPath $DllTarget -Destination $PkgDll -Force
Write-Host "      Synced package DLL: $PkgDll" -ForegroundColor Green

# 2. Compile Static Library (.a)
Write-Host "[2/3] Building Static Archive (libvivyqu_core.a)..." -ForegroundColor Yellow
$ObjDir = Join-Path $BuildDir "obj"
New-Item -ItemType Directory -Force -Path $ObjDir | Out-Null
$Objs = @()
foreach ($src in $Sources) {
    $baseName = [System.IO.Path]::GetFileNameWithoutExtension($src)
    $obj = Join-Path $ObjDir ($baseName + ".o")
    & clang++ -c @Flags $src -o $obj
    $Objs += $obj
}
$LibTarget = Join-Path $BinDir "libvivyqu_core.a"
& llvm-ar rcs $LibTarget $Objs
Write-Host "      Built: $LibTarget" -ForegroundColor Green

# 3. Compile Microbenchmark Harness
Write-Host "[3/4] Building Microbenchmark Harness (bench_core_latency.exe)..." -ForegroundColor Yellow
$BenchTarget = Join-Path $BinDir "bench_core_latency.exe"
& clang++ @Flags @Sources "$RootDir/tests/microbench/bench_core_latency.cpp" -o $BenchTarget
Write-Host "      Built: $BenchTarget" -ForegroundColor Green

# 4. Compile Shared Memory IPC Daemon
Write-Host "[4/4] Building Shared Memory IPC Daemon (vivyqu_shm_daemon.exe)..." -ForegroundColor Yellow
$DaemonTarget = Join-Path $BinDir "vivyqu_shm_daemon.exe"
& clang++ @Flags @Sources "$RootDir/src/ipc/shm_daemon.cpp" -o $DaemonTarget
Write-Host "      Built: $DaemonTarget" -ForegroundColor Green

Write-Host "`n=========================================================" -ForegroundColor Cyan
Write-Host "SUCCESS: Core libraries, daemon, and microbenchmark compiled!" -ForegroundColor Cyan
Write-Host "=========================================================" -ForegroundColor Cyan

if ($RunBenchmark) {
    Write-Host "`nLaunching Microbenchmark...`n" -ForegroundColor Yellow
    & $BenchTarget
}
