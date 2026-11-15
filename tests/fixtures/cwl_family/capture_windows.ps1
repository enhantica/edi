# Native historical capture only. Invoke inside the current locked Windows Pixi environment.
param(
    [Parameter(Mandatory=$true)][string]$Product,
    [Parameter(Mandatory=$true)][string]$Engine,
    [Parameter(Mandatory=$true)][string]$Output
)
$ErrorActionPreference = 'Stop'
$Product = (Resolve-Path $Product).Path
$Engine = (Resolve-Path $Engine).Path
$Output = [System.IO.Path]::GetFullPath($Output)
if (Test-Path $Output) { throw 'Historical capture requires a fresh output directory' }
New-Item -ItemType Directory $Output | Out-Null
$EngineBuild = Join-Path $Output 'engine-build'
$ProductBuild = Join-Path $Output 'product-build'
$Prefix = Join-Path $Output 'original-sdk'
$Artifacts = Join-Path $Output 'artifacts'
$Transcript = Join-Path $Output 'capture.log'
Start-Transcript -Path $Transcript | Out-Null
function Checked([string]$Program, [string[]]$Arguments) {
    Write-Host ($Program + ' ' + ($Arguments -join ' '))
    & $Program @Arguments
    if ($LASTEXITCODE -ne 0) { throw ($Program + ' failed: ' + $LASTEXITCODE) }
}
try {
    $env:OMP_NUM_THREADS = '1'
    $env:OPENBLAS_NUM_THREADS = '1'
    foreach ($Pair in @(@($Product, '7a8eabf53084332a10b90991907d2040e5365b6a'), @($Engine, 'b9f2267451adf1896463c706a87fea20790d28ac'))) {
        $Actual = (& git -C $Pair[0] rev-parse HEAD | Out-String).Trim()
        if ($LASTEXITCODE -ne 0 -or $Actual -ne $Pair[1]) { throw 'Capture refuses a non-original source before building' }
        Checked -Program 'git' -Arguments @('-C', $Pair[0], 'diff', '--exit-code', 'HEAD')
    }
    Checked -Program 'cmake' -Arguments @('-S', $Engine, '-B', $EngineBuild, '-G', 'Ninja', '-DCMAKE_BUILD_TYPE=Release', '-DCRYSTA_CXX_PACKAGE=ON', ('-DCMAKE_INSTALL_PREFIX=' + $Prefix))
    Checked -Program 'cmake' -Arguments @('--build', $EngineBuild, '--target', 'crysta_cli', '--parallel', '4')
    Checked -Program 'cmake' -Arguments @('--install', $EngineBuild, '--config', 'Release')
    Checked -Program 'cmake' -Arguments @('-S', $Product, '-B', $ProductBuild, '-G', 'Ninja', '-DCMAKE_BUILD_TYPE=Release', '-DEDI_BUILD_APP=OFF', ('-Dcrysta_DIR=' + ($Prefix + '/lib/cmake/crysta')), ('-DCMAKE_PREFIX_PATH=' + $Prefix))
    Checked -Program 'cmake' -Arguments @('--build', $ProductBuild, '--target', '_edi', '--parallel', '4')
    $Modules = @(Get-ChildItem -Path $ProductBuild -Recurse -Filter '_edi*.pyd')
    if ($Modules.Count -ne 1) { throw 'Capture requires exactly one freshly built Edi module' }
    $ImportDirectory = Join-Path $ProductBuild 'python/edi'
    New-Item -ItemType Directory -Force $ImportDirectory | Out-Null
    $ImportModule = Join-Path $ImportDirectory $Modules[0].Name
    if ($Modules[0].FullName -ne $ImportModule) { Copy-Item $Modules[0].FullName $ImportModule }
    $OriginalCli = Join-Path $Prefix 'bin/crysta.exe'
    $Stamp = (& $OriginalCli --build-commit | Out-String).Trim()
    if ($LASTEXITCODE -ne 0 -or $Stamp -ne 'b9f2267451adf1896463c706a87fea20790d28ac') { throw 'Wrong actual original engine build' }
    [System.IO.File]::WriteAllText((Join-Path $ProductBuild '.crysta-linked-sha'), $Stamp + "`n", [System.Text.UTF8Encoding]::new($false))
    Checked -Program 'python' -Arguments @((Join-Path $PSScriptRoot 'capture_windows.py'), '--product', $Product, '--engine', $Engine, '--build', $ProductBuild, '--engine-build', $EngineBuild, '--prefix', $Prefix, '--work', (Join-Path $Output 'work'), '--output', $Artifacts)
    [System.IO.File]::WriteAllText((Join-Path $Output 'capture.exit'), "0`n")
} catch {
    [System.IO.File]::WriteAllText((Join-Path $Output 'capture.exit'), "1`n")
    throw
} finally {
    Stop-Transcript | Out-Null
}
