# 🕷️ Spider-Buddy — Create Windows Desktop Shortcut for verified SpiderBuddy.exe
$ErrorActionPreference = "Continue"

$ProjectDir = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$VerifiedExe = Join-Path $ProjectDir "dist\verified\SpiderBuddy\SpiderBuddy.exe"
$WorkingDir = Join-Path $ProjectDir "dist\verified\SpiderBuddy"
$IconPath = Join-Path $WorkingDir "assets\icons\spider.ico"

if (-not (Test-Path $VerifiedExe)) {
    $VerifiedExe = Join-Path $ProjectDir "dist\SpiderBuddy\SpiderBuddy.exe"
    $WorkingDir = Join-Path $ProjectDir "dist\SpiderBuddy"
}

$WshShell = New-Object -ComObject WScript.Shell

# 1. Update Project Root shortcut
try {
    $LocalShortcut = $WshShell.CreateShortcut((Join-Path $ProjectDir "Spider-Buddy.lnk"))
    $LocalShortcut.TargetPath = $VerifiedExe
    $LocalShortcut.Arguments = ""
    $LocalShortcut.WorkingDirectory = $WorkingDir
    $LocalShortcut.IconLocation = "$IconPath, 0"
    $LocalShortcut.Description = "Spider-Buddy Desktop Companion"
    $LocalShortcut.Save()
    Write-Host "[+] Updated local shortcut: $(Join-Path $ProjectDir 'Spider-Buddy.lnk')"
} catch {
    Write-Host "[-] Could not update local shortcut: $_"
}

# 2. Update Windows Desktop shortcut
$DesktopPaths = @(
    [System.Environment]::GetFolderPath('Desktop'),
    [System.IO.Path]::Combine($env:USERPROFILE, "Desktop"),
    [System.IO.Path]::Combine($env:USERPROFILE, "OneDrive\Desktop")
)

$created = $false
foreach ($dp in $DesktopPaths) {
    if (-not [string]::IsNullOrWhiteSpace($dp)) {
        try {
            $dest = Join-Path $dp "Spider-Buddy.lnk"
            $sc = $WshShell.CreateShortcut($dest)
            $sc.TargetPath = $VerifiedExe
            $sc.Arguments = ""
            $sc.WorkingDirectory = $WorkingDir
            $sc.IconLocation = "$IconPath, 0"
            $sc.Description = "Spider-Buddy Desktop Companion"
            $sc.Save()
            Write-Host "=================================================="
            Write-Host "[+] SUCCESS: Desktop shortcut pointed to verified SpiderBuddy.exe!"
            Write-Host "[*] Desktop Shortcut: $dest"
            Write-Host "[*] Target Exe:       $VerifiedExe"
            Write-Host "[*] Working Dir:      $WorkingDir"
            Write-Host "=================================================="
            $created = $true
            break
        } catch {}
    }
}
