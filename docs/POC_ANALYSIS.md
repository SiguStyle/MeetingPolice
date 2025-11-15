# POC Transcript & Agenda 分析手順

`/poc` でアップロードしたアジェンダと音声は、FastAPI 側で `job_id` ごとに保存されています。以下の API で取得・分析できます。

1. **ジョブの開始**
   - `POST /api/poc/start` に `agenda` (任意) と `audio` を multipart で送信。
   - レスポンスに `{"job_id": "xxxxx"}` が返る。
2. **リアルタイム文字起こし**
   - `ws://<host>/api/poc/ws/{job_id}` に接続すると、`{"type":"transcript","payload":{...}}` が順次届く。
3. **完了後のデータ取得**
   - `GET /api/poc/jobs/{job_id}` でアジェンダテキストと transcript 配列をまとめて取得。
4. **Bedrock / Comprehend 連携例**
   - `POST /api/poc/jobs/{job_id}/analyze` はバックエンド内で `summarize_transcript` (Bedrock) と `analyze_sentiment` (Comprehend) を呼び、結果を JSON で返す。
   - 実運用ではこのエンドポイントを参考にして、`agenda_text + transcript_text` を独自のプロンプトに組み込み Bedrock へ渡し、Comprehend には `transcript_text` の塊ごとに `detect_sentiment` などを実行する。

## 推奨ワークフロー

1. `/poc` でファイルをアップロードし、リアルタイムに文字起こしを確認。
2. 完了後に `GET /api/poc/jobs/{job_id}` で JSON を取得して保存。
3. まとめたテキストを下記のように Bedrock に渡し、要約・アクションアイテムを生成。
4. 同じテキストを Comprehend に渡して感情分析やエンティティ抽出を行い、議題ごとの温度感を把握。

```python
from services.bedrock_utils import summarize_transcript
from services.comprehend_utils import analyze_sentiment

combined_text = agenda_text + "\n" + transcript_text
summary = summarize_transcript(job_id, combined_text)
sentiment = analyze_sentiment(transcript_text)
```

このフローにより、実際の AWS 連携に進む前に UI/UX とデータの流れをローカルで検証できます。
