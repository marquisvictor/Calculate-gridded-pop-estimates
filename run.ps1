param(
    [string]$State = 'Ogun',
    [string[]]$Lga = @('Abeokuta North', 'Abeokuta South'),
    [string[]]$Ward = @(),
    [ValidateSet('ward','lga','area')][string]$Level = 'ward',
    [string]$Out = '',
    [switch]$Plot
)
$ErrorActionPreference = 'Stop'
$pythonCandidates = @(
    (Join-Path $PSScriptRoot '.venv\Scripts\python.exe')
)
$pythonExe = $pythonCandidates | Where-Object { Test-Path -LiteralPath $_ } | Select-Object -First 1
if (-not $pythonExe) { throw 'Create .venv and install requirements.txt as described in README.md.' }
$rasterPath = Join-Path $PSScriptRoot 'data\NGA_population_v3_0_gridded.tif'
$boundaryPath = Join-Path $PSScriptRoot ('data\' + $State.ToLower().Replace(' ', '_') + '_wards_v3.geojson')
if (-not (Test-Path -LiteralPath $rasterPath) -or -not (Test-Path -LiteralPath $boundaryPath)) {
    & $pythonExe (Join-Path $PSScriptRoot 'estimate_population.py') download --state $State --out (Join-Path $PSScriptRoot 'data')
    if ($LASTEXITCODE -ne 0) { throw 'Data download failed.' }
}
if (-not $Out) { $Out = Join-Path $PSScriptRoot ('results\run_' + (Get-Date -Format 'yyyyMMdd_HHmmss_fff')) }
$cliArgs = @('estimate','--raster',$rasterPath,'--boundaries',$boundaryPath,'--state',$State,'--level',$Level,
    '--year','2025','--population-version','3.0','--boundary-version','3.0','--out',$Out)
foreach ($item in $Lga) { $cliArgs += @('--lga',$item) }
foreach ($item in $Ward) { $cliArgs += @('--ward',$item) }
if ($Plot) { $cliArgs += '--plot' }
& $pythonExe (Join-Path $PSScriptRoot 'estimate_population.py') @cliArgs
if ($LASTEXITCODE -ne 0) { throw 'Population estimation failed; see the error above.' }
