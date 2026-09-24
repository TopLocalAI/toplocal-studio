# Smoke test of the bundled Windows runtime (CI has no GPU, so engines are only load-tested).
$ErrorActionPreference = "Stop"
$Gen = (Resolve-Path "$PSScriptRoot/../app/src-tauri/generated").Path
$Py = Join-Path $Gen "runtime/python/python.exe"
$Engines = Join-Path $Gen "engines"
$Data = Join-Path $env:RUNNER_TEMP "toplocal-smoke"
if (-not $env:RUNNER_TEMP) { $Data = Join-Path $env:TEMP "toplocal-smoke" }

# Windows-specific process helpers: liveness check (os.kill would terminate) and spawning
# an engine with a hidden window through the job runner.
$env:PYTHONUTF8 = "1"  # as set by the desktop shell
$env:LOCALAI_FFMPEG = Join-Path $Engines "ffmpeg.exe"
& $Py -c @"
import asyncio, os, subprocess, sys
from localai_service import procs, jobs, config
assert procs.is_alive(os.getpid())
p = subprocess.Popen([sys.executable, '-c', 'pass']); p.wait()
assert not procs.is_alive(p.pid), 'exited process reported alive'
job = jobs.Job(module='smoke', task='ffmpeg', params={})
out = asyncio.run(job.run([config.FFMPEG, '-hide_banner', '-version']))
assert 'ffmpeg version' in out, out[:200]
slow = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(60)'], **procs.spawn_kwargs())
procs.kill_tree(slow.pid); slow.wait(timeout=10)
print('process helpers ok')
"@
if ($LASTEXITCODE -ne 0) { throw "process helper check failed" }

# Service starts, answers with the token and reports Windows + Vulkan.
$env:LOCALAI_DATA_DIR = $Data
$env:LOCALAI_MODELS_DIR = Join-Path $Data "models"
$env:LOCALAI_TOKEN = "smoke-token"
$env:LOCALAI_BUNDLED = "1"
$svc = Start-Process $Py -ArgumentList "-m", "localai_service", "--port", "4399" -PassThru -NoNewWindow
try {
    $ok = $false
    for ($i = 0; $i -lt 30 -and -not $ok; $i++) {
        Start-Sleep 1
        try { $ok = (Invoke-RestMethod "http://127.0.0.1:4399/api/health").ok } catch { }
    }
    if (-not $ok) { throw "service did not start" }
    $h = @{ "X-LocalAI-Token" = "smoke-token" }
    $sys = Invoke-RestMethod "http://127.0.0.1:4399/api/system" -Headers $h
    $sys | ConvertTo-Json -Depth 4 | Write-Host
    $models = Invoke-RestMethod "http://127.0.0.1:4399/api/models" -Headers $h
    $image = $models.models | Where-Object { $_.id -eq "image.zimage" }
    if ($image.engine -ne "stable-diffusion.cpp") { throw "Windows should use stable-diffusion.cpp, got $($image.engine)" }
    try { Invoke-RestMethod "http://127.0.0.1:4399/api/system" | Out-Null; throw "request without token was accepted" }
    catch { if ($_.Exception.Message -like "*without token*") { throw } }
} finally {
    Stop-Process -Id $svc.Id -Force -ErrorAction SilentlyContinue
}

# Engines load (DLLs resolve). Without a GPU driver the Vulkan loader may be missing, so
# a failure here is reported but does not fail the build.
foreach ($exe in "audiocpp/audiocpp_cli.exe", "llama/llama-completion.exe", "sdcpp/sd-cli.exe") {
    $path = Join-Path $Engines $exe
    $p = Start-Process $path -ArgumentList "--help" -NoNewWindow -Wait -PassThru -RedirectStandardOutput "$Data-$($exe -replace '/', '-').txt"
    if ($p.ExitCode -eq 0) { Write-Host "$exe --help ok" }
    else { Write-Host "::warning::$exe --help exited with $($p.ExitCode) (expected on runners without a Vulkan driver)" }
}
Write-Host "smoke test passed"
