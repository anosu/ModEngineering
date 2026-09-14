#requires -Version 7.0
[CmdletBinding()]
param(
    [Parameter(Mandatory)][string]$RepositoryRoot,
    [ValidateSet('Debug', 'Release')][string]$Configuration = 'Release',
    [string]$ExpectedVersion,
    [ValidateRange(60, 1800)][int]$TimeoutSeconds = 600
)
$ErrorActionPreference = 'Stop'
$repo = (Resolve-Path -LiteralPath $RepositoryRoot).Path
$config = Get-Content -LiteralPath (Join-Path $repo 'mod.json') -Raw | ConvertFrom-Json
if ($config.kind -ne 'android') { throw 'This release entry point is for Android Mods.' }
$project = Join-Path $repo $config.project

function Invoke-Dotnet([string[]]$Arguments) {
    $start = [Diagnostics.ProcessStartInfo]::new((Get-Command dotnet).Source)
    $start.WorkingDirectory = $repo
    $start.UseShellExecute = $false
    $start.CreateNoWindow = $true
    $start.RedirectStandardOutput = $true
    $start.RedirectStandardError = $true
    foreach ($argument in $Arguments) { [void]$start.ArgumentList.Add($argument) }
    $process = [Diagnostics.Process]::new()
    $process.StartInfo = $start
    try {
        [void]$process.Start()
        $stdout = $process.StandardOutput.ReadToEndAsync()
        $stderr = $process.StandardError.ReadToEndAsync()
        if (-not $process.WaitForExit($TimeoutSeconds * 1000)) {
            $process.Kill($true)
            $process.WaitForExit()
            throw 'dotnet timed out.'
        }
        $output = $stdout.GetAwaiter().GetResult()
        $errors = $stderr.GetAwaiter().GetResult()
        if ($process.ExitCode -ne 0) { throw "dotnet failed ($($process.ExitCode)):`n$output`n$errors" }
        if ($errors.Trim()) { Write-Host $errors }
        return $output
    } finally { $process.Dispose() }
}

$properties = (Invoke-Dotnet @('msbuild', $project, '-nologo', "-p:Configuration=$Configuration", '-p:UsePinnedSharedDependencies=true', '-getProperty:Version,TargetPath,TargetDir') | ConvertFrom-Json).Properties
$version = $properties.Version
if ($version -notmatch '^[0-9]+\.[0-9]+\.[0-9]+(?:[-.][0-9A-Za-z.-]+)?$') { throw "Invalid version: $version" }
if ($ExpectedVersion -and $ExpectedVersion.TrimStart('v') -cne $version) { throw "Tag $ExpectedVersion does not match version $version." }
Write-Host (Invoke-Dotnet @('build', $project, '-c', $Configuration, '--nologo', '--no-incremental', '-p:UsePinnedSharedDependencies=true'))
$assembly = [Reflection.Assembly]::LoadFile($properties.TargetPath)
$type = $assembly.GetType("$($config.assembly).ModInfo", $false)
if ($null -eq $type -or $type.GetField('Version').GetRawConstantValue() -cne $version) { throw 'Compiled ModInfo.Version does not match the project version.' }

function Resolve-Contained([string]$Root, [string]$Relative) {
    $full = [IO.Path]::GetFullPath((Join-Path $Root $Relative))
    $prefix = [IO.Path]::GetFullPath($Root).TrimEnd('\', '/') + [IO.Path]::DirectorySeparatorChar
    if (-not $full.StartsWith($prefix, [StringComparison]::OrdinalIgnoreCase)) { throw "Path escaped root: $Relative" }
    return $full
}

$inputs = [ordered]@{}
foreach ($item in $config.package.files) {
    if ($item.destination -match '(^/|\\|(^|/)\.\.(/|$))' -or $inputs.Contains($item.destination)) { throw "Invalid or duplicate archive path: $($item.destination)" }
    $source = if ($item.source.StartsWith('output/')) {
        Resolve-Contained $properties.TargetDir $item.source.Substring(7)
    } else { Resolve-Contained $repo $item.source }
    if (-not (Test-Path -LiteralPath $source -PathType Leaf)) { throw "Package input missing: $source" }
    $inputs[$item.destination] = $source
}
$directory = Resolve-Contained $repo "artifacts/release/v$version"
[void][IO.Directory]::CreateDirectory($directory)
$archivePath = Resolve-Contained $directory $config.package.name
$temporary = "$archivePath.$([Guid]::NewGuid().ToString('N')).tmp"
$archive = $null
try {
    $archive = [IO.Compression.ZipFile]::Open($temporary, [IO.Compression.ZipArchiveMode]::Create)
    foreach ($name in $inputs.Keys) {
        $entry = $archive.CreateEntry($name, [IO.Compression.CompressionLevel]::Optimal)
        $entry.LastWriteTime = [DateTimeOffset]::new(1980, 1, 1, 0, 0, 0, [TimeSpan]::Zero)
        $inputStream = [IO.File]::OpenRead($inputs[$name])
        $outputStream = $entry.Open()
        try { $inputStream.CopyTo($outputStream) }
        finally { $outputStream.Dispose(); $inputStream.Dispose() }
    }
    $archive.Dispose()
    $archive = $null
    [IO.File]::Move($temporary, $archivePath, $true)
} finally {
    if ($null -ne $archive) { $archive.Dispose() }
    if (Test-Path -LiteralPath $temporary) { Remove-Item -LiteralPath $temporary }
}
$archive = [IO.Compression.ZipFile]::OpenRead($archivePath)
try {
    if (($archive.Entries.FullName -join "`n") -cne ($inputs.Keys -join "`n")) { throw 'Archive layout verification failed.' }
    foreach ($entry in $archive.Entries) {
        $stream = $entry.Open()
        $sha = [Security.Cryptography.SHA256]::Create()
        try { $hash = [Convert]::ToHexString($sha.ComputeHash($stream)) }
        finally { $stream.Dispose(); $sha.Dispose() }
        if ($hash -ne (Get-FileHash -LiteralPath $inputs[$entry.FullName] -Algorithm SHA256).Hash) { throw "Archive content mismatch: $($entry.FullName)" }
    }
} finally { $archive.Dispose() }
$hash = (Get-FileHash -LiteralPath $archivePath -Algorithm SHA256).Hash.ToLowerInvariant()
[IO.File]::WriteAllText((Join-Path $directory 'SHA256SUMS.txt'), "$hash  $($config.package.name)`n", [Text.UTF8Encoding]::new($false))
[ordered]@{ Version = "v$version"; Archive = $archivePath; Sha256 = $hash; Entries = @($inputs.Keys) } | ConvertTo-Json -Depth 4
