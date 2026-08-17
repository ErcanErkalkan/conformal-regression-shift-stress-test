$ErrorActionPreference = "Stop"

# Run from:
# C:\CFSUASMAS\real_data_benchmark_v0_3
#
# Expected active environment:

$root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Set-Location $root
$env:PYTHONPATH = (Join-Path $root "code")

$jobs = @(
    @("ccpp",              0,  0,  5),
    @("ccpp",              0,  5, 10),
    @("ccpp",              0, 10, 15),
    @("ccpp",              0, 15, 20),

    @("superconductivity", 2,  0,  5),
    @("superconductivity", 2,  5, 10),
    @("superconductivity", 2, 10, 15),
    @("superconductivity", 2, 15, 20)
)

New-Item -ItemType Directory -Force .\runs\radial_shards | Out-Null

foreach ($job in $jobs) {
    $dataset = $job[0]
    $index   = $job[1]
    $start   = $job[2]
    $end     = $job[3]

    Write-Host ""
    Write-Host "========================================"
    Write-Host "RADIAL: $dataset repetitions $start-$end"
    Write-Host "========================================"

    python .\code\run_real_benchmark.py `
      --dataset $dataset `
      --dataset-index $index `
      --rep-start $start `
      --rep-end $end `
      --shift-mode radial `
      --config .\configs\real_data_prelock.json `
      --data-dir .\data\canonical `
      --out .\runs\radial_shards

    if ($LASTEXITCODE -ne 0) {
        throw "FAILED: radial $dataset repetitions $start-$end"
    }
}

python .\code\run_real_benchmark.py `
  --merge `
  --run-dir .\runs\radial_shards `
  --out .\runs\final_radial_v03

if ($LASTEXITCODE -ne 0) {
    throw "FAILED: radial merge"
}

Write-Host ""
Write-Host "========================================"
Write-Host "RADIAL MERGE MANIFEST"
Write-Host "========================================"
Get-Content .\runs\final_radial_v03\merge_manifest_real_v03.json

Write-Host ""
Write-Host "Expected radial result rows: 600"
Write-Host "Expected radial seed rows: 120"
Write-Host ""
Get-ChildItem .\runs\final_radial_v03
