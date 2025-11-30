#!/usr/bin/env python3
"""シナリオ①の音声ファイルを結合"""
from pathlib import Path
import sys
sys.path.append("scripts")
from merge_audio_files import merge_audio_files

# 入力フォルダ
input_dir = Path("docs/test/シナリオ①")

# 音声ファイルを取得して更新日時順にソート
input_files = sorted(input_dir.glob("*.wav"), key=lambda f: f.stat().st_mtime)

# 出力ファイル
output_file = Path("docs/test/scenario1_merged.wav")

print("=" * 60)
print("🎤 シナリオ①音声結合")
print("=" * 60)
print()
print(f"📂 入力フォルダ: {input_dir}")
print(f"📄 見つかったファイル（更新日時順）:")
for i, file in enumerate(input_files, 1):
    print(f"  {i}. {file.name}")
print()

# 結合実行（無音なし）
merge_audio_files(input_files, output_file, silence_duration=0)

print()
print("✨ 完成！")
