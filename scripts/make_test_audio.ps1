# Generates a spoken test clip with the Windows speech synthesizer so the whole
# pipeline can be exercised without recording a microphone.
#
# Usage:
#   powershell -ExecutionPolicy Bypass -File scripts/make_test_audio.ps1
#   powershell -ExecutionPolicy Bypass -File scripts/make_test_audio.ps1 -Out out.wav

param(
    [string]$Out = "tests/fixtures/sample_lecture.wav",
    [string]$Text = "Today we will discuss retrieval augmented generation. First, the lecturer explains how documents are split into chunks. Then each chunk is embedded into a vector space. The system retrieves the most relevant chunks before answering the student's question."
)

$ErrorActionPreference = "Stop"

$directory = Split-Path -Parent $Out
if ($directory -and -not (Test-Path $directory)) {
    New-Item -ItemType Directory -Path $directory -Force | Out-Null
}

Add-Type -AssemblyName System.Speech
$synth = New-Object System.Speech.Synthesis.SpeechSynthesizer
try {
    $synth.Rate = -1
    $synth.Volume = 100
    $synth.SetOutputToWaveFile((Resolve-Path -LiteralPath $directory).Path + "\" + (Split-Path -Leaf $Out))
    $synth.Speak($Text)
}
finally {
    $synth.Dispose()
}

$file = Get-Item $Out
Write-Host ("wrote {0} ({1:N1} KB)" -f $file.FullName, ($file.Length / 1KB))
