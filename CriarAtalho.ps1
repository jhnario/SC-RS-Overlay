param([string]$Destination = [Environment]::GetFolderPath('Desktop'))
$ErrorActionPreference = 'Stop'
$shortcutPath = Join-Path $Destination 'SC - Leitor RS.lnk'
$shell = New-Object -ComObject WScript.Shell
$shortcut = $shell.CreateShortcut($shortcutPath)
$shortcut.TargetPath = Join-Path $PSScriptRoot 'Iniciar.cmd'
$shortcut.WorkingDirectory = $PSScriptRoot
$shortcut.IconLocation = (Join-Path $PSScriptRoot 'nave.ico') + ',0'
$shortcut.WindowStyle = 7
$shortcut.Description = 'SC - Leitor de assinaturas de minerais e salvage'
$shortcut.Save()
Write-Host 'Atalho com icone de nave criado.'
