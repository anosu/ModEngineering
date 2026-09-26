#requires -Version 7.0
[CmdletBinding()]
param(
    [Parameter(Mandatory)][string]$RepositoryRoot,
    [Parameter(Mandatory)][string]$InteropDirectory,
    [Parameter(Mandatory)][string]$MelonLoaderDirectory
)
$ErrorActionPreference = 'Stop'
$repo = (Resolve-Path -LiteralPath $RepositoryRoot).Path
$sets = @(
    @{ Source = $InteropDirectory; Target = 'dependencies/interop/assemblies' },
    @{ Source = $MelonLoaderDirectory; Target = 'dependencies/melonloader/net6' }
)

# The tracked DLL filenames are the dependency list. Validate every source before copying.
$copies = @()
foreach ($set in $sets) {
    $target = Join-Path $repo $set.Target
    if (-not (Test-Path -LiteralPath $target -PathType Container)) {
        throw "Missing tracked dependency directory: $target"
    }
    $files = @(Get-ChildItem -LiteralPath $target -Filter '*.dll' -File)
    if ($files.Count -eq 0) { throw "No tracked DLLs in $target" }
    $sourceRoot = if ([IO.Path]::IsPathRooted($set.Source)) { $set.Source } else { Join-Path $repo $set.Source }
    foreach ($file in $files) {
        $source = Join-Path $sourceRoot $file.Name
        if (-not (Test-Path -LiteralPath $source -PathType Leaf)) { throw "Missing dependency: $source" }
        $copies += @{ Source = $source; Target = $file.FullName }
    }
}
foreach ($copy in $copies) {
    if ([IO.Path]::GetFullPath($copy.Source) -ne [IO.Path]::GetFullPath($copy.Target)) {
        Copy-Item -LiteralPath $copy.Source -Destination $copy.Target -Force
    }
}
Write-Host "Synchronized $($copies.Count) DLLs from the local exports."
