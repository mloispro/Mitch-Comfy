function Get-AitkDopTimerEvidence {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)]
        [string[]]$Paths,

        [Parameter(Mandatory)]
        [ValidateRange(1, [int]::MaxValue)]
        [int]$Steps,

        [Parameter(Mandatory)]
        [ValidateRange(1, [int]::MaxValue)]
        [int]$PerformanceLogEvery,

        [ValidateRange(1, [int]::MaxValue)]
        [int]$TimerMaxBuffer = 10,

        [ValidateRange(0, [int]::MaxValue)]
        [int]$StartStep = 0
    )

    if ($StartStep -ge $Steps) { throw "StartStep must be lower than Steps." }

    # AI-Toolkit's Timer stores a bounded deque. BaseSDTrainProcess records one
    # prior-prediction timing per completed update, prints and resets the deque
    # on performance-log steps, skips printing at the initial step, and does not
    # print the final partial deque after the loop. Simulate that exact behavior
    # so timer output can be reconciled with the complete update range without
    # treating unprinted samples as missing executions.
    $expectedValues = [System.Collections.Generic.List[int]]::new()
    $bufferCount = 0
    $ringBufferDropped = 0
    foreach ($step in $StartStep..($Steps - 1)) {
        if ($bufferCount -eq $TimerMaxBuffer) {
            $ringBufferDropped += 1
        } else {
            $bufferCount += 1
        }
        if ($step -ne $StartStep -and $step % $PerformanceLogEvery -eq 0) {
            $expectedValues.Add($bufferCount)
            $bufferCount = 0
        }
    }
    $finalUnflushed = $bufferCount
    $expectedReported = [int](($expectedValues | Measure-Object -Sum).Sum)
    $expectedProven = $expectedReported + $ringBufferDropped + $finalUnflushed
    $expectedUpdates = $Steps - $StartStep
    if ($expectedProven -ne $expectedUpdates) {
        throw "Internal DOP timer accounting error: expected $expectedUpdates updates, reconciled $expectedProven."
    }

    $logs = [System.Collections.Generic.List[object]]::new()
    foreach ($path in $Paths) {
        if (-not (Test-Path -LiteralPath $path -PathType Leaf)) { throw "Missing DOP evidence log: $path" }
        $text = Get-Content -Raw -LiteralPath $path
        $matches = [regex]::Matches(
            $text,
            'prior predict,\s*num\s*=\s*([1-9][0-9]*)',
            [Text.RegularExpressions.RegexOptions]::IgnoreCase
        )
        $actualValues = @($matches | ForEach-Object { [int]$_.Groups[1].Value })
        $sequenceValid = $actualValues.Count -eq $expectedValues.Count
        if ($sequenceValid) {
            for ($index = 0; $index -lt $actualValues.Count; $index++) {
                if ($actualValues[$index] -ne $expectedValues[$index]) {
                    $sequenceValid = $false
                    break
                }
            }
        }
        $logs.Add([ordered]@{
            path = $path
            record_count = $actualValues.Count
            reported_updates = [int](($actualValues | Measure-Object -Sum).Sum)
            expected_record_count = $expectedValues.Count
            expected_reported_updates = $expectedReported
            sequence_valid = $sequenceValid
        })
    }

    $allSequencesValid = @($logs | Where-Object { -not $_.sequence_valid }).Count -eq 0
    return [ordered]@{
        valid = $allSequencesValid
        steps = $Steps
        start_step = $StartStep
        performance_log_every = $PerformanceLogEvery
        timer_max_buffer = $TimerMaxBuffer
        expected_record_count_per_log = $expectedValues.Count
        expected_reported_updates_per_log = $expectedReported
        ring_buffer_dropped_updates = $ringBufferDropped
        final_unflushed_updates = $finalUnflushed
        proven_updates = if ($allSequencesValid) { $expectedProven } else { 0 }
        logs = @($logs)
    }
}
