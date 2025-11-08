# MeetingPolice

MeetingPolice は、会議参加者にリアルタイムの音声解析結果を提供し、管理者には議題管理や要約生成を支援するためのデモ実装です。フロントエンドは Vite + React、バックエンドは FastAPI を採用し、AWS（Transcribe / Comprehend / Bedrock / S3）と Vonage Video への接続を前提としています。

## ディレクトリ構成と役割

- `backend/`
  - FastAPI アプリ本体。`main.py` でルータを束ね、`config.py` が環境変数を一括管理します。
  - `session/`: 参加者向け API。Vonage トークン発行と WebSocket 経由のトランスクリプト配信を担当。
  - `admin/`: 管理者向け API。会議 CRUD と Bedrock を使った要約生成を実装。
  - `services/`: AWS / Vonage など外部サービスとの連携層。`bedrock_utils.py`, `s3_storage.py`, `transcribe_stream.py` などが boto3 クライアントをラップし、接続不能時はローカルフォールバックを提供します。
  - `models/`: Pydantic スキーマ（会議、アジェンダ、サマリーなど）。
  - `utils/`: 認証・ログ・時刻処理等の共通ユーティリティ。
  - `data/`: JSON ベースの簡易永続化領域（git には `.gitkeep` のみ含む想定）。
- `frontend/`
  - `session-app/`: 参加者 UI。参加者グリッド、感情メトリクス、ミュート操作などを表示し、将来的に WebSocket からのライブ分析結果を描画します。
  - `admin-app/`: 管理 UI。会議一覧／作成フォーム／要約パネルを備え、Bedrock/S3 から取得したデータを可視化します。
  - どちらも `src/components`, `src/hooks`, `src/services`, `src/pages` など共通構成で整理しています。
- `docs/`: 仕様メモ (`AGENTS.md`)、API 定義補足 (`API_SPEC.md`)、アーキテクチャ図など。
- `scripts/`: `start_dev.sh`（FastAPI + 2 つの Vite Dev Server を起動）、`deploy.sh`、`.env` テンプレート生成、S3 同期ツールなど開発・運用スクリプト群。
- `nginx/`: 静的配信と FastAPI へのリバースプロキシを定義した `default.conf` を格納。
- `tests/`: pytest ベースのテスト。Bedrock/S3/Transcribe 連携をモックで検証する `test_bedrock.py` `test_s3_storage.py` `test_transcribe.py` などを配置。
- `secrets/`: Vonage RSA 秘密鍵等の機密ファイルを置くディレクトリ（`.gitignore` 済み）。

## 主要技術と連携ポイント

- **AWS 連携**: `config.py` / `.env` でリージョンや資格情報を設定し、`services/` 層で boto3 クライアントを生成。S3/Bedrock/Transcribe/Comprehend すべてにローカルフォールバックを用意しているため、ネットワークなしでも開発できます。
- **Vonage Video**: `services/vonage_client.py` が JWT を発行し、`session` ルートから払い出します。鍵未設定時はモックトークンが返るため UI の結線確認が容易です。
- **永続化**: `services/repository.py` が会議メタデータを `backend/data/meetings.json` に保存し、サマリー／トランスクリプトは `services/s3_storage.py` 経由で S3 またはローカル `backend/data/s3/` に書き込みます。

## 開発手順

1. `cp .env.example .env` で環境変数を準備し、AWS/Vonage の値を設定します。
2. `secrets/vonage_private.key` に RSA 秘密鍵を配置します（ローカル動作のみなら空のままでもモックトークンが使用されます）。
3. `./scripts/start_dev.sh` を実行すると、Python 仮想環境の構築 → FastAPI 起動 → 2 つの Vite Dev Server 起動が自動で行われます。
4. テストは `pytest` を使用します。AWS 関連は Stubber/モックでカバーされるため、実ネットワークなしで実行可能です。

### 代表的な利用フロー

1. 管理者は `admin-app` からミーティングを作成し、表示された Meeting ID を参加者に共有します。
2. 参加者は `session-app` の参加フォームに Meeting ID を入力して Vonage セッションに参加します（初回参加時に自動でセッション ID を払い出し、会議ステータスを `live` に更新）。
3. 音声ストリームは `/api/session/ws/{meeting_id}` の WebSocket で受信し、Transcribe/Comprehend を通じたサマリーがリアルタイムに配信されます（現状はモックデータをストリームしています）。
4. 会議終了後は `admin-app` からサマリー生成 API を叩き、結果を S3（もしくはローカルフォールバック）に保存します。

## ドキュメント

- `docs/AGENTS.md`: 音声解析エージェントの仕様メモ
- `docs/API_SPEC.md`: REST / WebSocket API の補足説明
- `docs/ARCHITECTURE_OVERVIEW.png`, `docs/SEQUENCE_DIAGRAM.png`: 全体設計・処理シーケンス図

この README を参照することで、リポジトリ全体の構成と各フォルダの役割、主要な連携ポイントが把握できます。
