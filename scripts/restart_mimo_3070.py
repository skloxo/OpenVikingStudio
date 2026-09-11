import subprocess
import base64

ps_code = """
$procs = Get-Process -Name "Xiaomi MiMo" -ErrorAction SilentlyContinue
if ($procs) {
    Write-Output "Stopping MiMo processes..."
    Stop-Process -Name "Xiaomi MiMo" -Force -ErrorAction SilentlyContinue
    Start-Sleep -Seconds 2
}

Write-Output "Restarting MiMo..."
$exe = "C:\\Program Files\\Xiaomi MiMo\\Xiaomi MiMo.exe"
if (Test-Path $exe) {
    Start-Process -FilePath $exe
    Start-Sleep -Seconds 3
    $newProcs = Get-Process -Name "Xiaomi MiMo" -ErrorAction SilentlyContinue
    Write-Output "New MiMo PIDs: $($newProcs.Id -join ", ")"
} else {
    Write-Output "MiMo executable not found at $exe"
}
"""

b64 = base64.b64encode(ps_code.encode("utf-16le")).decode("ascii")
cmd = [
    "sshpass", "-p", "Skl3289568",
    "ssh", "-p", "6022",
    "-o", "StrictHostKeyChecking=no",
    "-o", "PubkeyAuthentication=no",
    "-o", "PreferredAuthentications=password",
    "-o", "ConnectTimeout=10",
    "AzureAD\\s@tide.red@8.129.0.26",
    f"powershell -EncodedCommand {b64}"
]
res = subprocess.run(cmd, capture_output=True, text=True, errors="replace")
print("STDOUT:\n", res.stdout)
if res.stderr:
    print("STDERR:\n", res.stderr)
