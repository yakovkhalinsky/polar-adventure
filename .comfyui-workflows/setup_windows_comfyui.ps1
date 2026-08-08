#Requires -Version 5.1
<#
.SYNOPSIS
    Downloads the recommended model stack for Polar Adventures into a local ComfyUI Desktop install.

.DESCRIPTION
    This script checks for ComfyUI Desktop in the standard Windows location, then downloads the
    SD 1.5 checkpoint, VAE, isometric LoRAs, ControlNet models, and installs the custom nodes
    needed by the polar-adventures asset pipeline.

.PARAMETER ComfyUiPath
    Path to your ComfyUI Desktop folder. Defaults to the standard Windows Desktop location.

.PARAMETER SkipModels
    Skip downloading model files (useful if you only want to install custom nodes).

.PARAMETER SkipNodes
    Skip installing custom nodes.

.EXAMPLE
    .\setup_windows_comfyui.ps1

.EXAMPLE
    .\setup_windows_comfyui.ps1 -ComfyUiPath "C:\Users\Yakov\Documents\ComfyUI"
#>
param(
    [string]$ComfyUiPath = "$env:USERPROFILE\Documents\ComfyUI",
    [switch]$SkipModels,
    [switch]$SkipNodes
)

$ErrorActionPreference = "Stop"

# -----------------------------------------------------------------------------
# Verify ComfyUI Desktop location
# -----------------------------------------------------------------------------
if (-not (Test-Path $ComfyUiPath)) {
    Write-Host "ERROR: ComfyUI Desktop folder not found at: $ComfyUiPath" -ForegroundColor Red
    Write-Host "Please pass the correct path with -ComfyUiPath"
    exit 1
}

$modelsDir = Join-Path $ComfyUiPath "models"
$customNodesDir = Join-Path $ComfyUiPath "custom_nodes"

foreach ($d in @("checkpoints", "vae", "loras", "controlnet")) {
    $full = Join-Path $modelsDir $d
    if (-not (Test-Path $full)) {
        New-Item -ItemType Directory -Path $full -Force | Out-Null
        Write-Host "Created folder: $full" -ForegroundColor DarkGray
    }
}

# -----------------------------------------------------------------------------
# Helper: download a file if it does not already exist
# -----------------------------------------------------------------------------
function Get-ModelFile {
    param(
        [string]$Url,
        [string]$Destination,
        [string]$Name
    )

    if (Test-Path $Destination) {
        Write-Host "  Already exists: $Name" -ForegroundColor Green
        return
    }

    Write-Host "  Downloading $Name..." -ForegroundColor Cyan
    Write-Host "     From: $Url" -ForegroundColor DarkGray
    try {
        $parent = Split-Path $Destination -Parent
        if (-not (Test-Path $parent)) {
            New-Item -ItemType Directory -Path $parent -Force | Out-Null
        }
        Invoke-WebRequest -Uri $Url -OutFile $Destination -UseBasicParsing
        Write-Host "     Saved to: $Destination" -ForegroundColor Green
    }
    catch {
        Write-Host "     FAILED: $_" -ForegroundColor Red
    }
}

# -----------------------------------------------------------------------------
# Models to download
# -----------------------------------------------------------------------------
$downloads = @(
    @{
        Name = "SD 1.5 base checkpoint"
        Url  = "https://huggingface.co/runwayml/stable-diffusion-v1-5/resolve/main/v1-5-pruned-emaonly.safetensors"
        Dest = Join-Path $modelsDir "checkpoints\v1-5-pruned-emaonly.safetensors"
    },
    @{
        Name = "Improved VAE"
        Url  = "https://huggingface.co/stabilityai/sd-vae-ft-mse-original/resolve/main/vae-ft-mse-840000-ema-pruned.safetensors"
        Dest = Join-Path $modelsDir "vae\vae-ft-mse-840000-ema-pruned.safetensors"
    },
    @{
        Name = "ControlNet OpenPose"
        Url  = "https://huggingface.co/lllyasviel/ControlNet-v1-1/resolve/main/control_v11p_sd15_openpose.pth"
        Dest = Join-Path $modelsDir "controlnet\control_v11p_sd15_openpose.pth"
    },
    @{
        Name = "ControlNet Canny"
        Url  = "https://huggingface.co/lllyasviel/ControlNet-v1-1/resolve/main/control_v11p_sd15_canny.pth"
        Dest = Join-Path $modelsDir "controlnet\control_v11p_sd15_canny.pth"
    }
)

if (-not $SkipModels) {
    Write-Host "`nDownloading recommended model stack..." -ForegroundColor Yellow
    foreach ($item in $downloads) {
        Get-ModelFile -Url $item.Url -Destination $item.Dest -Name $item.Name
    }

    Write-Host "`nLoRA note:" -ForegroundColor Yellow
    Write-Host "  You must download LoRAs manually from Civitai because they require login." -ForegroundColor Cyan
    Write-Host "  Put them in: $(Join-Path $modelsDir 'loras')" -ForegroundColor Cyan
    Write-Host "  Recommended:" -ForegroundColor Cyan
    Write-Host "    - Zavy's Cute Isometric Tiles (SDXL)  -> https://civarchive.com/models/340599?modelVersionId=381373" -ForegroundColor Cyan
    Write-Host "    - Wolfie's Isometric Scenes (SDXL)     -> https://civitai.com/models/593055/wolfies-isometric-scenes-sdxl-concept" -ForegroundColor Cyan
    Write-Host "    - DarkoIsometricStyle (SDXL)           -> https://civitai.com/models/1954920/darkoisometricstyle" -ForegroundColor Cyan
    Write-Host "    - Witchpot/icestage (arctic flavor)    -> https://huggingface.co/Witchpot/icestage" -ForegroundColor Cyan
}

# -----------------------------------------------------------------------------
# Custom nodes to install
# -----------------------------------------------------------------------------
$nodes = @(
    @{ Repo = "https://github.com/huchenlei/ComfyUI-layerdiffuse.git"; Name = "ComfyUI-layerdiffuse" },
    @{ Repo = "https://github.com/Jcd1230/rembg-comfyui-node.git"; Name = "rembg-comfyui-node" },
    @{ Repo = "https://github.com/JosefKuchar/ComfyUI-AdvancedTiling.git"; Name = "ComfyUI-AdvancedTiling" }
)

if (-not $SkipNodes) {
    Write-Host "`nInstalling custom nodes..." -ForegroundColor Yellow
    foreach ($node in $nodes) {
        $target = Join-Path $customNodesDir $node.Name
        if (Test-Path $target) {
            Write-Host "  Already installed: $($node.Name)" -ForegroundColor Green
        }
        else {
            Write-Host "  Installing $($node.Name)..." -ForegroundColor Cyan
            try {
                git clone $node.Repo $target
                Write-Host "    Installed: $($node.Name)" -ForegroundColor Green
            }
            catch {
                Write-Host "    FAILED: $_" -ForegroundColor Red
                Write-Host "    Make sure git is on your PATH." -ForegroundColor Red
            }
        }
    }
}

Write-Host "`nSetup complete. Restart ComfyUI Desktop to load new models and nodes." -ForegroundColor Green
Write-Host "Then run from the project repository:" -ForegroundColor Cyan
Write-Host "  python3 .comfyui-workflows/generate_polar_assets_v3.py --mode sd15" -ForegroundColor Cyan
