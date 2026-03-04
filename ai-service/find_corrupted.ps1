# find_corrupted.ps1
# Run this script from your project root directory

Write-Host "🔍 Searching for corrupted files with random strings..." -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

$projectRoot = Get-Location
$corruptedFiles = @()

# Pattern to match random-looking strings (30+ chars, mix of letters/numbers)
$pattern = '[A-Za-z0-9]{30,}'

# Search all Python files
Get-ChildItem -Path $projectRoot -Recurse -Filter "*.py" | ForEach-Object {
    $content = Get-Content $_.FullName -Raw
    if ($content -match $pattern) {
        $matches = [regex]::Matches($content, $pattern)
        foreach ($match in $matches) {
            if ($match.Value -notmatch 'http|https|www|settings|config|token|key|password|secret') {
                Write-Host "❌ Found in: $($_.FullName)" -ForegroundColor Red
                Write-Host "   String: $($match.Value)" -ForegroundColor Yellow
                Write-Host "   Line around match:"
                $lines = $content.Split("`n")
                for ($i = 0; $i -lt $lines.Count; $i++) {
                    if ($lines[$i] -match [regex]::Escape($match.Value)) {
                        Write-Host "   Line $($i+1): $($lines[$i].Trim())" -ForegroundColor Gray
                        $corruptedFiles += $_.FullName
                    }
                }
                Write-Host ""
            }
        }
    }
}

# Also search for specific random string
$specificString = "ArQuMHtpwbtsTXsRMArUQeWyGrRu7gwbZs2"
Write-Host "🔍 Searching for specific corrupted string: $specificString" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

Get-ChildItem -Path $projectRoot -Recurse -Filter "*.py" | ForEach-Object {
    $content = Get-Content $_.FullName -Raw
    if ($content -match $specificString) {
        Write-Host "❌ Found in: $($_.FullName)" -ForegroundColor Red
        Write-Host "   Line around match:"
        $lines = $content.Split("`n")
        for ($i = 0; $i -lt $lines.Count; $i++) {
            if ($lines[$i] -match $specificString) {
                Write-Host "   Line $($i+1): $($lines[$i].Trim())" -ForegroundColor Yellow
                $corruptedFiles += $_.FullName
            }
        }
        Write-Host ""
    }
}
