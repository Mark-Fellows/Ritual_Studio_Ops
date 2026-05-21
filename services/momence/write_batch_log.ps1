# write_batch_log.ps1
# -------------------
# Retry-capable batch-log appender. Called by Run_Momence_Chain.bat and
# Run_Momence_Retry_Past.bat in place of every inline `Add-Content`.
#
# Usage from cmd:
#   powershell -NoProfile -ExecutionPolicy Bypass -File write_batch_log.ps1 -Message "your text"
#
# Reads the target file from $env:BATCH_LOG. Retries up to 6 times with a
# 5-second delay between attempts to survive transient OneDrive / antivirus
# file locks. On final failure writes a one-line warning to stderr (which is
# captured by the chain's per-run log) but does NOT raise — the chain must
# never abort because a log write failed.

param(
    [Parameter(Mandatory = $true)]
    [string]$Message
)

$ErrorActionPreference = 'Stop'

$batchLog = $env:BATCH_LOG
if ([string]::IsNullOrWhiteSpace($batchLog)) {
    Write-Host "[BATCH-LOG] BATCH_LOG env var is empty — skipping write" -ErrorAction SilentlyContinue
    exit 0
}

# Ensure the parent directory exists (cheap idempotent op).
try {
    $dir = Split-Path -LiteralPath $batchLog -Parent
    if ($dir -and -not (Test-Path -LiteralPath $dir)) {
        New-Item -ItemType Directory -Path $dir -Force | Out-Null
    }
} catch {
    # Non-fatal — Add-Content will surface a clearer error if the dir is bad.
}

$timestamp = (Get-Date -Format 'yyyy-MM-dd HH:mm:ss')
$line = "$timestamp - $Message"

$maxAttempts = 6
$attempt = 0
$lastError = $null

while ($attempt -lt $maxAttempts) {
    $attempt++
    try {
        Add-Content -LiteralPath $batchLog -Encoding utf8 -Value $line
        exit 0
    } catch {
        $lastError = $_
        if ($attempt -lt $maxAttempts) {
            Start-Sleep -Seconds 5
        }
    }
}

# Final failure — emit to stderr so the chain's per-run log captures it.
[Console]::Error.WriteLine("[BATCH-LOG WRITE FAILED after $maxAttempts attempts: $lastError] $line")
exit 0
