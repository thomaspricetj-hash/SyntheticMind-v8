# Recursively scan all headers and detect include loops

$root = "C:\Users\thomas price\Desktop\bitdrop\include"

Write-Host "Scanning headers for include recursion..."
Write-Host ""

$includes = @{}

# Build include graph
Get-ChildItem -Path $root -Recurse -Filter *.h | ForEach-Object {
    $file = $_.FullName
    $text = Get-Content $file

    $inc = @()
    foreach ($line in $text) {
        if ($line -match '#include\s+"(.+)"') {
            $inc += $matches[1]
        }
    }

    $includes[$file] = $inc
}

# DFS to detect cycles
$visited = @{}
$stack = @{}

function Visit($file) {
    if ($stack.ContainsKey($file) -and $stack[$file]) {
        Write-Host "🔥 INCLUDE LOOP DETECTED:" -ForegroundColor Red
        Write-Host "   $file"
        return $true
    }

    if ($visited.ContainsKey($file) -and $visited[$file]) {
        return $false
    }

    $visited[$file] = $true
    $stack[$file] = $true

    foreach ($inc in $includes[$file]) {
        $target = Join-Path $root $inc
        if (Test-Path $target) {
            if (Visit $target) {
                Write-Host "   ↳ $file"
                return $true
            }
        }
    }

    $stack[$file] = $false
    return $false
}

foreach ($file in $includes.Keys) {
    Visit $file | Out-Null
}

Write-Host ""
Write-Host "Scan complete."

