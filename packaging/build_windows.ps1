# Build the self-contained runtime bundled into the Windows installer:
#   generated/runtime/python   standalone CPython 3.12 + service (no PyTorch)
#   generated/engines/         audio.cpp, llama.cpp and stable-diffusion.cpp (Vulkan), ffmpeg
# Engines are upstream release binaries pinned in windows-engines.json (url + sha256).
# Runs on GitHub Actions (windows-2022) or any Windows machine with uv installed.
$ErrorActionPreference = "Stop"
$PSNativeCommandUseErrorActionPreference = $true  # a failing uv/python call stops the build
$ProgressPreference = "SilentlyContinue"
$env:UV_PYTHON_PREFERENCE = "only-managed"  # a python-build-standalone copy, not the runner's Python

$Root = (Resolve-Path "$PSScriptRoot/..").Path
$Out = Join-Path $Root "app/src-tauri/generated"
$Cache = Join-Path $Root ".cache/windows-engines"
$Lock = Get-Content (Join-Path $PSScriptRoot "windows-engines.json") -Raw | ConvertFrom-Json

function Fetch($entry) {
    New-Item -ItemType Directory -Force $Cache | Out-Null
    $file = Join-Path $Cache ([IO.Path]::GetFileName($entry.url))
    if (-not (Test-Path $file) -or (Get-FileHash $file -Algorithm SHA256).Hash -ne $entry.sha256.ToUpper()) {
        Write-Host "download $($entry.url)"
        Invoke-WebRequest $entry.url -OutFile $file
    }
    $hash = (Get-FileHash $file -Algorithm SHA256).Hash
    if ($hash -ne $entry.sha256.ToUpper()) { throw "sha256 mismatch for $file ($hash)" }
    return $file
}

function Expand($entry, $dest) {
    $zip = Fetch $entry
    $tmp = Join-Path $Cache ("x-" + [IO.Path]::GetFileNameWithoutExtension($zip))
    if (Test-Path $tmp) { Remove-Item -Recurse -Force $tmp }
    Expand-Archive $zip $tmp
    New-Item -ItemType Directory -Force $dest | Out-Null
    return $tmp
}

Remove-Item -Recurse -Force (Join-Path $Out "runtime"), (Join-Path $Out "engines") -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Force (Join-Path $Out "runtime"), (Join-Path $Out "engines") | Out-Null

# 1. Private copy of a standalone CPython. Never install into the shared uv install.
uv python install 3.12
$PySrc = (uv python find 3.12).Trim()
$PyHome = Split-Path $PySrc
$Runtime = Join-Path $Out "runtime/python"
Copy-Item -Recurse $PyHome $Runtime
$Py = Join-Path $Runtime "python.exe"
Remove-Item -Force (Join-Path $Runtime "Lib/EXTERNALLY-MANAGED") -ErrorAction SilentlyContinue
if (-not (Resolve-Path $Py).Path.StartsWith($Out)) { throw "refusing to install outside $Out" }

$Wheels = Join-Path $Out ".wheels"
Remove-Item -Recurse -Force $Wheels -ErrorAction SilentlyContinue
uv build -q --wheel --no-sources (Join-Path $Root "service") -o $Wheels
uv pip install -q --python $Py --break-system-packages --no-sources (Get-ChildItem $Wheels/*.whl).FullName certifi
Remove-Item -Recurse -Force $Wheels

# ffmpeg from the imageio-ffmpeg wheel, then drop the package itself.
uv pip install -q --python $Py --break-system-packages imageio-ffmpeg
$Ffmpeg = (& $Py -c "import imageio_ffmpeg; print(imageio_ffmpeg.get_ffmpeg_exe())").Trim()
Copy-Item $Ffmpeg (Join-Path $Out "engines/ffmpeg.exe")
uv pip uninstall -q --python $Py --break-system-packages imageio-ffmpeg

# Trim what never runs in the app.
foreach ($d in "Lib/test", "Lib/idlelib", "Lib/tkinter", "Lib/turtledemo", "Lib/ensurepip", "Lib/site-packages/pip",
               "tcl", "include", "libs", "Scripts") {
    Remove-Item -Recurse -Force (Join-Path $Runtime $d) -ErrorAction SilentlyContinue
}
Get-ChildItem $Runtime -Recurse -Directory -Filter "__pycache__" | Remove-Item -Recurse -Force
# Precompile once so the app never writes __pycache__ into Program Files. A few stdlib
# test fixtures do not compile; that is expected and not an error.
$PSNativeCommandUseErrorActionPreference = $false
& $Py -m compileall -q -j 0 --invalidation-mode unchecked-hash (Join-Path $Runtime "Lib") | Out-Null
$PSNativeCommandUseErrorActionPreference = $true

# 2. Native engines.
$Engines = Join-Path $Out "engines"

$src = Expand $Lock.audiocpp (Join-Path $Engines "audiocpp")
Copy-Item (Join-Path $src "audiocpp_cli.exe"), (Join-Path $src "*.dll") (Join-Path $Engines "audiocpp")
Copy-Item -Recurse (Join-Path $src "model_specs") (Join-Path $Engines "audiocpp/model_specs")
Copy-Item (Join-Path $src "LICENSE") (Join-Path $Engines "audiocpp/LICENSE.txt")
$Vad = Join-Path $Engines "audiocpp/assets/framework/models/silero_vad"
New-Item -ItemType Directory -Force $Vad | Out-Null
Copy-Item (Fetch $Lock.silero_vad) (Join-Path $Vad "silero_vad_16k.safetensors")

$src = Expand $Lock.llama (Join-Path $Engines "llama")
Copy-Item (Join-Path $src "llama-completion.exe"), (Join-Path $src "*.dll") (Join-Path $Engines "llama")
Copy-Item (Join-Path $src "LICENSE*") (Join-Path $Engines "llama") -ErrorAction SilentlyContinue

$src = Expand $Lock.sdcpp (Join-Path $Engines "sdcpp")
Copy-Item (Join-Path $src "sd-cli.exe"), (Join-Path $src "*.dll"), (Join-Path $src "*.txt") (Join-Path $Engines "sdcpp")

# Fail the build if anything still points back into the development checkout.
$editable = Get-ChildItem (Join-Path $Runtime "Lib/site-packages") -Recurse -Include "*.pth", "direct_url.json" |
    Select-String -Pattern '"editable":\s*true' -List
if ($editable) { throw "editable install found in runtime: $editable" }

foreach ($d in "runtime", "engines") {
    $size = (Get-ChildItem (Join-Path $Out $d) -Recurse -File | Measure-Object Length -Sum).Sum / 1MB
    Write-Host ("{0,-8} {1,6:N0} MB" -f $d, $size)
}
