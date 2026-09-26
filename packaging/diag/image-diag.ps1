# TopLocal Studio image diagnostics (Windows): renders the same prompt and seed with different
# engine settings so we can see which one produces clean pictures on this GPU.
# Output: Desktop\toplocal-diag\*.png and *.log. Takes a few minutes.
$ErrorActionPreference = "Continue"
$app = Join-Path $env:LOCALAPPDATA "TopLocal Studio"
$sd = Join-Path $app "engines\sdcpp\sd-cli.exe"
$models = Join-Path $env:LOCALAPPDATA "ai.toplocal.studio\models"
$out = Join-Path ([Environment]::GetFolderPath("Desktop")) "toplocal-diag"
New-Item -ItemType Directory -Force -Path $out | Out-Null
if (-not (Test-Path $sd)) { Write-Host "sd-cli.exe not found at $sd"; exit 1 }

$zimg = @("--diffusion-model", "$models\image\sdcpp\z-image-turbo\z_image_turbo-Q4_K.gguf",
          "--vae", "$models\image\sdcpp\vae-flux1\ae.safetensors",
          "--llm", "$models\llm\Qwen3-4B-Instruct-2507-Q4_K_M.gguf",
          "--cfg-scale", "1.0", "--steps", "8", "-s", "42")
$prompt = "An orange cat lying on a sunny windowsill, soft afternoon light, realistic photo"

function Run($name, $base, $size, $extra, $vars) {
  $cmdArgs = @($base) + @("-p", $prompt, "-W", $size, "-H", $size, "-o", "$out\$name.png") + $extra
  foreach ($k in $vars.Keys) { Set-Item "env:$k" $vars[$k] }
  $t = Get-Date
  & $sd @cmdArgs *> "$out\$name.log"
  foreach ($k in $vars.Keys) { Remove-Item "env:$k" -ErrorAction SilentlyContinue }
  Write-Host ("{0,-28} {1,5:N0}s  exit {2}" -f $name, ((Get-Date) - $t).TotalSeconds, $LASTEXITCODE)
}

$noCm2 = @{ GGML_VK_DISABLE_COOPMAT2 = "1" }
$noCm = @{ GGML_VK_DISABLE_COOPMAT2 = "1"; GGML_VK_DISABLE_COOPMAT = "1" }
if (Test-Path "$models\image\sdcpp\z-image-turbo") {
  Run "zimage-hd-1-default"     $zimg 1440 @("--diffusion-fa") @{}
  Run "zimage-hd-2-vae-tiling"  $zimg 1440 @("--diffusion-fa", "--vae-tiling") @{}
  Run "zimage-hd-3-no-coopmat"  $zimg 1440 @("--diffusion-fa") $noCm
  Run "zimage-hd-4-no-fa"       $zimg 1440 @() @{}
}
Write-Host "`nDone. Pictures and logs are in $out"
Start-Process explorer.exe $out
