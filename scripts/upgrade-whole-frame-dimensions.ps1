function Get-UpgradePngDimensions([string]$Path) {
    $stream=[IO.File]::OpenRead($Path)
    try {
        $header=[byte[]]::new(24)
        if ($stream.Read($header,0,24) -ne 24 -or [BitConverter]::ToString($header[0..7]) -ne '89-50-4E-47-0D-0A-1A-0A') { throw 'Expected PNG input.' }
        $width=([int]$header[16] -shl 24) -bor ([int]$header[17] -shl 16) -bor ([int]$header[18] -shl 8) -bor [int]$header[19]
        $height=([int]$header[20] -shl 24) -bor ([int]$header[21] -shl 16) -bor ([int]$header[22] -shl 8) -bor [int]$header[23]
        if ($width -le 0 -or $height -le 0) { throw 'Invalid PNG dimensions.' }
        return @($width,$height)
    } finally { $stream.Dispose() }
}

function Get-UpgradeWholeFrameDimensions([int]$Width,[int]$Height) {
    if ($Width -le 0 -or $Height -le 0) { throw 'Positive input dimensions required.' }
    $a=$Width;$b=$Height
    while ($b -ne 0) { $remainder=$a%$b;$a=$b;$b=$remainder }
    $p=$Width/$a;$q=$Height/$a
    # Reduced p/q are coprime, so a multiple-of-16 scale factor guarantees
    # both dimensions are model-compatible without cropping or aspect distortion.
    $factor=[Math]::Max(16,[Math]::Round([Math]::Sqrt(1048576/($p*$q))/16)*16)
    $outWidth=[int]($p*$factor);$outHeight=[int]($q*$factor)
    $pixels=[long]$outWidth*$outHeight
    if ($pixels -lt 786432 -or $pixels -gt 1310720) { throw 'Exact aspect cannot fit the bounded one-megapixel evaluation budget.' }
    return @($outWidth,$outHeight)
}
