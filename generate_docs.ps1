# generate_docs.ps1
#
# Generates the pyjallib API documentation (HTML) with pdoc.
# This script only generates files. It does not commit or publish anything;
# review the output and publish it yourself.
#
# Usage:
#   .\generate_docs.ps1
#   .\generate_docs.ps1 -SourceRoot <repository root> -OutputDirectory <output directory>
#
# -SourceRoot       Repository root that contains src\pyjallib and docs_support.
#                   Default: the directory of this script.
# -OutputDirectory  Where the HTML is written. Default: <SourceRoot>\docs.
#
# pdoc is fetched for this run only (uv run --with pdoc). It is not added to the
# project dependencies. The exit code is non-zero when generation fails.

param(
    [string]$SourceRoot = $PSScriptRoot,
    [string]$OutputDirectory = ""
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path -LiteralPath $SourceRoot -PathType Container)) {
    Write-Host "SourceRoot not found: $SourceRoot" -ForegroundColor Red
    exit 1
}
$SourceRoot = (Resolve-Path -LiteralPath $SourceRoot).Path

if (-not $OutputDirectory) {
    $OutputDirectory = Join-Path $SourceRoot "docs"
}

$buildScript = Join-Path $SourceRoot "docs_support\build_docs.py"

Write-Host "Generating pdoc documentation for pyjallib..." -ForegroundColor Cyan
Write-Host "  source: $SourceRoot"
Write-Host "  output: $OutputDirectory"

& uv run --project $SourceRoot --frozen --with pdoc python $buildScript --source-root $SourceRoot --output $OutputDirectory
$generationExitCode = $LASTEXITCODE

if ($generationExitCode -ne 0) {
    Write-Host "Failed to generate docs (exit code $generationExitCode). Check the errors above." -ForegroundColor Red
    exit $generationExitCode
}

Write-Host "Docs generated: $OutputDirectory" -ForegroundColor Green
exit 0
