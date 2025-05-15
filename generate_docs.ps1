# generate_docs.ps1

Write-Host "`n🔧 Installing dependencies..." -ForegroundColor Cyan

# Install required packages
uv pip install pdoc
uv pip install .

Write-Host "`n🔧 Generating pdoc documentation for PyJalLib..." -ForegroundColor Cyan

# Set 3ds Max Python path (수정 필요 시 여기를 바꾸세요)
$maxPythonPath = "C:\Program Files\Autodesk\3ds Max 2025\Python\Lib\site-packages"
$projectPath = (Get-Location).Path
$env:PYTHONPATH = "$maxPythonPath;$projectPath"

# Generate docs using pdoc
python -c "from pathlib import Path; import docs_support.mock_pymxs; import pdoc; pdoc.pdoc('pyjallib', output_directory=Path('docs'))"

if ($LASTEXITCODE -eq 0) {
    Write-Host "`n✅ Docs generated successfully. Committing..." -ForegroundColor Green

    git add docs
    git commit -m "Update API docs"
    git push origin main

    Write-Host "`n🚀 Docs committed and pushed to GitHub!" -ForegroundColor Green
} else {
    Write-Host "`n❌ Failed to generate docs. Please check for errors above." -ForegroundColor Red
}

