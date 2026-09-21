# Pure dimension/graph preparation for the isolated native Qwen reference-packing test.
function Get-UpgradeQwenAlignedDimensions([int]$Width,[int]$Height) {
    if ($Width -le 0 -or $Height -le 0) { throw 'Positive image dimensions required.' }
    $scale=[Math]::Sqrt(1048576.0/([double]$Width*$Height))
    $outWidth=[int]([Math]::Round($Width*$scale/32)*32)
    $outHeight=[int]([Math]::Round($Height*$scale/32)*32)
    if ($outWidth -le 0 -or $outHeight -le 0) { throw 'Unsupported reference aspect ratio.' }
    return @($outWidth,$outHeight)
}

function Get-UpgradeOrientedImageDimensions([string]$Path) {
    Add-Type -AssemblyName System.Drawing
    $photo=[Drawing.Image]::FromFile([IO.Path]::GetFullPath($Path))
    try {
        $width=$photo.Width;$height=$photo.Height
        if ($photo.PropertyIdList -contains 274) {
            $orientation=[BitConverter]::ToUInt16($photo.GetPropertyItem(274).Value,0)
            if ($orientation -in 5,6,7,8) { $temporary=$width;$width=$height;$height=$temporary }
        }
        return @($width,$height)
    } finally { $photo.Dispose() }
}
