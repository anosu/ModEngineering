#requires -Version 7.0
[CmdletBinding()]
param(
    [Parameter(Mandatory)][string]$RepositoryRoot,
    [Parameter(Mandatory)][string]$InteropDirectory,
    [Parameter(Mandatory)][string]$MelonLoaderDirectory
)
$ErrorActionPreference = 'Stop'
$repo = (Resolve-Path -LiteralPath $RepositoryRoot).Path
$config = Get-Content -LiteralPath (Join-Path $repo 'mod.json') -Raw | ConvertFrom-Json
[xml]$project = Get-Content -LiteralPath (Join-Path $repo $config.project) -Raw
$sets = @(
    @{ Property = 'GameInteropReferenceDirectory'; Source = $InteropDirectory; Target = 'dependencies/interop/assemblies' },
    @{ Property = 'MelonLoaderReferenceDirectory'; Source = $MelonLoaderDirectory; Target = 'dependencies/melonloader/net6' }
)
# Validate both sets before copying anything. Unrelated files are never deleted.
$copies = @()
foreach ($set in $sets) {
    $prefix = '$(' + $set.Property + ')/'
    $count = 0
    foreach ($reference in $project.Project.ItemGroup.Reference) {
        if ($null -eq $reference) { continue }
        $hint = [string]$reference.HintPath
        if (-not $hint.Replace('\', '/').StartsWith($prefix)) { continue }
        $name = $hint.Replace('\', '/').Substring($prefix.Length)
        if ($name -match '[/\\]' -or $name -notmatch '\.dll$') { throw "Invalid reference: $hint" }
        $source = Join-Path $set.Source $name
        if (-not (Test-Path -LiteralPath $source -PathType Leaf)) { throw "Missing reference: $source" }
        $copies += @{ Source = $source; Target = (Join-Path (Join-Path $repo $set.Target) $name) }
        $count++
    }
    if ($count -eq 0) { throw "No declared references for $($set.Property)" }
}
foreach ($copy in $copies) {
    [void][IO.Directory]::CreateDirectory([IO.Path]::GetDirectoryName($copy.Target))
    if ([IO.Path]::GetFullPath($copy.Source) -ne [IO.Path]::GetFullPath($copy.Target)) {
        Copy-Item -LiteralPath $copy.Source -Destination $copy.Target -Force
    }
}
Write-Host "Synchronized $($copies.Count) declared dependencies. Full exports remain outside tracked reference directories."
