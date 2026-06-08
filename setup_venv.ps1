$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ScriptPath = Join-Path $ScriptDir "setup_venv.py"

if (Get-Command python -ErrorAction SilentlyContinue) {
    & python $ScriptPath @args
    exit $LASTEXITCODE
}

if (Get-Command py -ErrorAction SilentlyContinue) {
    & py -3 $ScriptPath @args
    exit $LASTEXITCODE
}

Write-Error "未找到 Python。请先安装 Python 3，并确保 python 或 py 在 PATH 中。"
exit 1
