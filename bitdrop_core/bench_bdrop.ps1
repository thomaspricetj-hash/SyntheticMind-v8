# bench_bdrop.ps1
param(
  [string]$exe = ".\build\Release\bdropc.exe",
  [string]$input = "input.bin",
  [string]$output = "out.bdrop",
  [int]$warmup = 1,
  [int]$iters = 10
)

function Time-Run($cmd, $arg1, $arg2) {
  $sw = [System.Diagnostics.Stopwatch]::StartNew()
  & $cmd $arg1 $arg2
  $sw.Stop()
  return $sw.Elapsed.TotalSeconds
}

Write-Host "Benchmark: $exe $input -> $output"
Write-Host "Warmup runs: $warmup, Measured runs: $iters"

# Warmup
for ($i=1; $i -le $warmup; $i++) {
  Write-Host "Warmup $i..."
  Time-Run $exe $input $output | Out-Null
  Start-Sleep -Seconds 1
}

# Measured runs
$times = New-Object System.Collections.Generic.List[double]
for ($i=1; $i -le $iters; $i++) {
  Write-Host "Run $i..."
  $t = Time-Run $exe $input $output
  Write-Host ("  Time: {0:N4} s" -f $t)
  $times.Add($t)
  Start-Sleep -Milliseconds 200
}

# Stats
$mean = ($times | Measure-Object -Average).Average
$sorted = $times | Sort-Object
$median = if ($sorted.Count % 2 -eq 1) { $sorted[([int]([math]::Floor($sorted.Count/2)))] } else { ($sorted[$sorted.Count/2 - 1] + $sorted[$sorted.Count/2]) / 2.0 }
$min = ($times | Measure-Object -Minimum).Minimum
$max = ($times | Measure-Object -Maximum).Maximum
$sumSquares = 0.0
foreach ($v in $times) { $sumSquares += ($v - $mean) * ($v - $mean) }
$std = if ($times.Count -gt 1) { [math]::Sqrt($sumSquares / ($times.Count - 1)) } else { 0.0 }

Write-Host ("Results (s): mean={0:N4} median={1:N4} std={2:N4} min={3:N4} max={4:N4}" -f $mean, $median, $std, $min, $max)

# Throughput (bytes/s) if input file exists
if ([string]::IsNullOrWhiteSpace($input) -eq $false -and (Test-Path -Path $input)) {
  $size = (Get-Item $input).Length
  $throughput = $size / $mean
  Write-Host ("Input size: {0:N0} bytes, Throughput: {1:N2} MB/s" -f $size, ($throughput / 1MB))
} else {
  Write-Host "Input file not found or input path empty; skipping throughput calculation."
}

