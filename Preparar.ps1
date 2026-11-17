$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
$python = Join-Path $PSScriptRoot 'portable\python.exe'
if (-not (Test-Path -LiteralPath $python)) {
    Write-Host 'Baixando Python portatil do site oficial...'
    $archive = Join-Path $PSScriptRoot 'python-portable.zip'
    Invoke-WebRequest 'https://www.python.org/ftp/python/3.12.10/python-3.12.10-embed-amd64.zip' -OutFile $archive -TimeoutSec 120
    Expand-Archive -LiteralPath $archive -DestinationPath (Join-Path $PSScriptRoot 'portable') -Force
}
$pth = Join-Path $PSScriptRoot 'portable\python312._pth'
@('python312.zip','.','..','import site') | Set-Content -LiteralPath $pth -Encoding ASCII
if (-not (Test-Path -LiteralPath (Join-Path $PSScriptRoot 'portable\Lib\site-packages\pip'))) {
    Write-Host 'Preparando dependencias...'
    $getpip = Join-Path $PSScriptRoot 'get-pip.py'
    Invoke-WebRequest 'https://bootstrap.pypa.io/get-pip.py' -OutFile $getpip -TimeoutSec 120
    & $python $getpip --disable-pip-version-check
    if ($LASTEXITCODE -ne 0) { throw 'Falha ao preparar pip.' }
}
& $python -m pip install --disable-pip-version-check -r requirements.txt
if ($LASTEXITCODE -ne 0) { throw 'Nao foi possivel instalar as dependencias.' }
& $python -m unittest -v
if ($LASTEXITCODE -ne 0) { throw 'Os testes falharam.' }
Set-Content -LiteralPath (Join-Path $PSScriptRoot '.ready') -Value '0.1'
Write-Host 'Pronto. Abra Iniciar.cmd.'



