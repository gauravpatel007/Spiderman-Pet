$WshShell = New-Object -ComObject WScript.Shell
$ProjectDir = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path

# Use system Python 3.13 pythonw where dependencies (PySide6, etc.) are installed
$pythonw = "pythonw.exe"
$sysPythonw = "C:\Program Files\Python313\pythonw.exe"
$venvPythonw = Join-Path $ProjectDir ".venv\Scripts\pythonw.exe"

if (Test-Path $sysPythonw) {
    $pythonw = $sysPythonw
} elseif (Test-Path $venvPythonw) {
    $pythonw = $venvPythonw
}

$DesktopPaths = @(
    [System.Environment]::GetFolderPath('Desktop'),
    (Join-Path $env:USERPROFILE "Desktop"),
    (Join-Path $env:USERPROFILE "OneDrive\Desktop"),
    "C:\Users\Gaurav Patel\OneDrive\Desktop"
)

$targetLnkPaths = @(
    (Join-Path $ProjectDir "Spider-Buddy.lnk")
)

foreach ($dp in $DesktopPaths) {
    if (-not [string]::IsNullOrWhiteSpace($dp) -and (Test-Path $dp)) {
        $targetLnkPaths += (Join-Path $dp "Spider-Buddy.lnk")
    }
}

$icon = Join-Path $ProjectDir "assets\icons\spider.ico"
$mainPy = Join-Path $ProjectDir "main.py"

foreach ($lnk in ($targetLnkPaths | Select-Object -Unique)) {
    try {
        $sc = $WshShell.CreateShortcut($lnk)
        $sc.TargetPath = $pythonw
        $sc.Arguments = "`"$mainPy`""
        $sc.WorkingDirectory = $ProjectDir
        if (Test-Path $icon) {
            $sc.IconLocation = "$icon, 0"
        }
        $sc.Description = "Spider-Buddy Desktop Companion"
        $sc.Save()
        Write-Host "[+] Updated shortcut cleanly (No terminal): $lnk"
    } catch {
        Write-Host "[-] Could not save shortcut $lnk : $_"
    }
}
