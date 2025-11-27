#!/usr/bin/env python3
"""
テスト用の会議音声を生成するスクリプト
AWS Pollyを使って、2人の話者（男性・女性）の音声を生成します
"""
from __future__ import annotations

import sys
from pathlib import Path
import wave

# プロジェクトのルートをパスに追加
project_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "backend"))

from utils.auth_aws import get_session
from config import get_settings

# 会話スクリプト
CONVERSATION = [
    {
        "speaker": "加藤（男性）",
        "voice_id": "Takumi",  # 日本語男性
        "text": """加藤です。本日は、モバイルアプリの初回チュートリアルで離脱が増えている件についてご報告します。
現在、プロフィール登録画面でユーザーが途中離脱しているケースが目立っています。
具体的には、メール認証の処理中に画面が止まったように見えてしまい、ユーザーが"本当に動いているのか"を判断できない状態が発生しています。
また、写真登録がスムーズに進まず、失敗したまま戻ってこないケースも複数確認されています。"""
    },
    {
        "speaker": "加藤（男性）",
        "voice_id": "Takumi",
        "text": """そのため、改善案として二点考えています。
まず一つ目は、登録処理の進行状況を画面上ではっきり見えるようにすることです。
『どれくらい待てばいいのか』が分かるだけでも離脱はかなり抑えられると考えています。"""
    },
    {
        "speaker": "加藤（男性）",
        "voice_id": "Takumi",
        "text": """二つ目は、写真登録がうまくいかなかった時に、ユーザーが迷わず再試行できる案内を画面に追加することです。
失敗に気づけない、または対処法が分からない、という状況をなくすことが目的です。
以上が、現状の課題と改善に向けた方向性です。
引き続き、具体的な設計案をまとめてまいりますので、ご確認をお願いできればと思います。"""
    },
    {
        "speaker": "リーダー（女性）",
        "voice_id": "Mizuki",  # 日本語女性
        "text": """加藤さん、報告ありがとう。状況がとても分かりやすかったです。
初回チュートリアルの離脱が増えているという点は、プロダクトとしても早めに対応したいところなので、今回のまとめは助かりました。"""
    },
    {
        "speaker": "リーダー（女性）",
        "voice_id": "Mizuki",
        "text": """特に、処理中に止まって見えてしまう点と、写真登録の失敗にユーザーが気づけない点は、確かにストレスになりやすいですね。
改善案として挙げてもらった"進行状況の見える化"と"再試行の案内追加"は、実装負荷も大きくなさそうですし、効果が見込みやすいと思います。"""
    },
    {
        "speaker": "リーダー（女性）",
        "voice_id": "Mizuki",
        "text": """この方向性で、もう少し画面イメージや対応の流れを整理して、デザインチームともすり合わせられる資料を一度作ってみてください。
こちらでも必要なところはサポートします。
いい視点でした、引き続きお願いします。"""
    },
]


def generate_audio_segment(text: str, voice_id: str) -> bytes:
    """AWS Pollyで音声を生成"""
    session = get_session()
    polly = session.client("polly", region_name=get_settings().aws_region)
    
    response = polly.synthesize_speech(
        Text=text,
        OutputFormat="pcm",
        VoiceId=voice_id,
        Engine="neural",  # ニューラル音声（高品質）
        SampleRate="16000",
    )
    
    return response["AudioStream"].read()


def combine_audio_segments(segments: list[bytes], silence_duration: float = 1.0) -> bytes:
    """複数の音声セグメントを結合（間に無音を挿入）"""
    sample_rate = 16000
    silence_samples = int(sample_rate * silence_duration * 2)  # 2バイト/サンプル
    silence = b"\x00" * silence_samples
    
    combined = b""
    for i, segment in enumerate(segments):
        combined += segment
        if i < len(segments) - 1:  # 最後以外は無音を追加
            combined += silence
    
    return combined


def save_as_wav(pcm_data: bytes, output_path: Path):
    """PCMデータをWAVファイルとして保存"""
    with wave.open(str(output_path), "wb") as wav_file:
        wav_file.setnchannels(1)  # モノラル
        wav_file.setsampwidth(2)  # 16bit
        wav_file.setframerate(16000)  # 16kHz
        wav_file.writeframes(pcm_data)


def main():
    print("🎤 テスト用音声を生成中...")
    print(f"話者数: {len(set(item['speaker'] for item in CONVERSATION))}人")
    print(f"セグメント数: {len(CONVERSATION)}個\n")
    
    # 各セグメントの音声を生成
    audio_segments = []
    for i, item in enumerate(CONVERSATION, 1):
        print(f"[{i}/{len(CONVERSATION)}] {item['speaker']}: {item['text'][:30]}...")
        try:
            audio_data = generate_audio_segment(item["text"], item["voice_id"])
            audio_segments.append(audio_data)
            print(f"  ✅ 生成完了 ({len(audio_data)} bytes)")
        except Exception as e:
            print(f"  ❌ エラー: {e}")
            return
    
    # 音声を結合
    print("\n🔗 音声を結合中...")
    combined_audio = combine_audio_segments(audio_segments, silence_duration=1.5)
    
    # 出力先
    output_dir = Path(__file__).resolve().parents[1] / "backend" / "data"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "test_meeting_audio.wav"
    
    # WAVファイルとして保存
    print(f"💾 保存中: {output_path}")
    save_as_wav(combined_audio, output_path)
    
    print(f"\n✨ 完了！")
    print(f"📁 ファイル: {output_path}")
    print(f"📊 サイズ: {output_path.stat().st_size / 1024:.1f} KB")
    print(f"⏱️  長さ: 約{len(combined_audio) / 16000 / 2:.1f}秒")
    
    # アジェンダファイルも生成
    agenda_path = output_dir / "test_meeting_agenda.txt"
    agenda_text = """・議題タイトル
モバイルアプリの初回チュートリアル離脱率改善検討

・発表者
加藤 真一

・所要時間
3分

・検討事項
初回チュートリアル中の「プロフィール登録画面」での離脱増加
- 登録途中で処理が止まっているように見える
- 写真登録がスムーズに進まない

・改善案
1. 進行状況を分かりやすく画面に表示
2. 写真登録失敗時の再試行案内を追加
"""
    agenda_path.write_text(agenda_text, encoding="utf-8")
    print(f"📄 アジェンダ: {agenda_path}")
    
    print("\n🚀 テストの実行方法:")
    print("1. フロントエンドで音声ファイルをアップロード")
    print(f"   音声: {output_path}")
    print(f"   アジェンダ: {agenda_path}")
    print("2. リアルタイム分析結果を確認")


if __name__ == "__main__":
    main()
