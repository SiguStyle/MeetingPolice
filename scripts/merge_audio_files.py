#!/usr/bin/env python3
"""
複数の音声ファイルを結合するスクリプト
Google Text-to-Speechなどでダウンロードした音声を1つにまとめます
"""
from __future__ import annotations

import argparse
import wave
from pathlib import Path


def read_wav_file(file_path: Path) -> tuple[bytes, int, int, int]:
    """WAVファイルを読み込む"""
    with wave.open(str(file_path), "rb") as wav:
        channels = wav.getnchannels()
        sample_width = wav.getsampwidth()
        framerate = wav.getframerate()
        frames = wav.readframes(wav.getnframes())
    return frames, channels, sample_width, framerate


def create_silence(duration_sec: float, channels: int, sample_width: int, framerate: int) -> bytes:
    """無音データを生成"""
    num_frames = int(framerate * duration_sec)
    return b"\x00" * (num_frames * channels * sample_width)


def merge_audio_files(input_files: list[Path], output_file: Path, silence_duration: float = 1.5):
    """
    複数の音声ファイルを結合
    
    Args:
        input_files: 入力ファイルのリスト（順番通りに結合）
        output_file: 出力ファイルのパス
        silence_duration: 音声間の無音時間（秒）
    """
    print(f"🎵 音声ファイルを結合中...")
    print(f"入力ファイル数: {len(input_files)}")
    print(f"無音時間: {silence_duration}秒\n")
    
    # 最初のファイルからパラメータを取得
    first_frames, channels, sample_width, framerate = read_wav_file(input_files[0])
    print(f"📊 音声パラメータ:")
    print(f"  チャンネル: {channels} ({'モノラル' if channels == 1 else 'ステレオ'})")
    print(f"  サンプル幅: {sample_width} bytes ({sample_width * 8} bit)")
    print(f"  サンプルレート: {framerate} Hz\n")
    
    # 無音データを生成
    silence = create_silence(silence_duration, channels, sample_width, framerate)
    
    # 全ての音声を結合
    combined_frames = b""
    for i, file_path in enumerate(input_files, 1):
        print(f"[{i}/{len(input_files)}] {file_path.name}")
        
        frames, file_channels, file_sample_width, file_framerate = read_wav_file(file_path)
        
        # パラメータが一致しているか確認
        if file_channels != channels or file_sample_width != sample_width or file_framerate != framerate:
            print(f"  ⚠️  警告: パラメータが異なります")
            print(f"     期待: {channels}ch, {sample_width}bytes, {framerate}Hz")
            print(f"     実際: {file_channels}ch, {file_sample_width}bytes, {file_framerate}Hz")
            print(f"  ⚠️  このファイルはスキップします")
            continue
        
        combined_frames += frames
        
        # 最後以外は無音を追加
        if i < len(input_files):
            combined_frames += silence
        
        duration = len(frames) / (framerate * channels * sample_width)
        print(f"  ✅ 追加完了 ({duration:.1f}秒)")
    
    # 結合した音声を保存
    print(f"\n💾 保存中: {output_file}")
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    with wave.open(str(output_file), "wb") as wav:
        wav.setnchannels(channels)
        wav.setsampwidth(sample_width)
        wav.setframerate(framerate)
        wav.writeframes(combined_frames)
    
    total_duration = len(combined_frames) / (framerate * channels * sample_width)
    file_size = output_file.stat().st_size / 1024
    
    print(f"\n✨ 完了！")
    print(f"📁 ファイル: {output_file}")
    print(f"📊 サイズ: {file_size:.1f} KB")
    print(f"⏱️  長さ: {total_duration:.1f}秒")


def main():
    parser = argparse.ArgumentParser(description="複数の音声ファイルを結合")
    parser.add_argument("input_files", nargs="*", help="結合する音声ファイル（順番通り）")
    parser.add_argument("-o", "--output", help="出力ファイル名")
    parser.add_argument("-s", "--silence", type=float, default=1.5, help="音声間の無音時間（秒）")
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("🎤 音声ファイル結合ツール")
    print("=" * 60)
    print()
    
    # 引数が指定されている場合
    if args.input_files:
        input_files = [Path(f) for f in args.input_files]
        output_file = Path(args.output) if args.output else Path("backend/data/merged_audio.wav")
        
        # ファイルの存在確認
        missing_files = [f for f in input_files if not f.exists()]
        if missing_files:
            print(f"❌ エラー: 以下のファイルが見つかりません:")
            for f in missing_files:
                print(f"  - {f}")
            return
        
        print(f"📄 入力ファイル:")
        for i, file in enumerate(input_files, 1):
            print(f"  {i}. {file}")
        print()
        
        # 結合実行
        merge_audio_files(input_files, output_file, silence_duration=args.silence)
        
        print()
        print("✨ 完成！")
        return
    
    # 引数なしの場合はデフォルト動作
    input_dir = Path("backend/data/audio_parts")
    output_file = Path("backend/data/test_meeting_audio.wav")
    
    # 入力ファイルを探す
    if not input_dir.exists():
        print(f"❌ エラー: {input_dir} が見つかりません")
        print()
        print("📝 使い方:")
        print(f"1. {input_dir} フォルダを作成")
        print("2. Google Text-to-Speechでダウンロードした音声ファイルを配置")
        print("   例: 01_kato_part1.wav, 02_kato_part2.wav, ...")
        print("3. このスクリプトを実行")
        print()
        print("💡 ファイル名は順番通りに並ぶように命名してください")
        print("   （01_, 02_, 03_... のように番号を付けると便利）")
        return
    
    # WAVファイルを取得（名前順にソート）
    input_files = sorted(input_dir.glob("*.wav"))
    
    if not input_files:
        print(f"❌ エラー: {input_dir} に音声ファイル（.wav）が見つかりません")
        print()
        print("📝 Google Text-to-Speechで音声を生成して、")
        print(f"   {input_dir} に保存してください")
        return
    
    print(f"📂 入力フォルダ: {input_dir}")
    print(f"📄 見つかったファイル:")
    for i, file in enumerate(input_files, 1):
        print(f"  {i}. {file.name}")
    print()
    
    # 結合実行
    merge_audio_files(input_files, output_file, silence_duration=1.5)
    
    print()
    print("🚀 次のステップ:")
    print("1. フロントエンドを起動")
    print("2. 音声ファイルをアップロード")
    print(f"   音声: {output_file}")
    print(f"   アジェンダ: backend/data/test_meeting_agenda.txt")
    print("3. リアルタイム分析結果を確認")


if __name__ == "__main__":
    main()
