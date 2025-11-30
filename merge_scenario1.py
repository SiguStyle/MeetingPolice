from scripts.merge_audio_files import merge_audio_files
from pathlib import Path

files = [
    Path('docs/test/シナリオ①音声1.wav'),
    Path('docs/test/シナリオ①音声2.wav'),
    Path('docs/test/シナリオ①音声3.wav'),
]

output = Path('docs/test/scenario1_merged.wav')

merge_audio_files(files, output, silence_duration=1.5)
