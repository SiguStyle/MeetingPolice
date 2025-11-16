import json
from io import BytesIO

from botocore.exceptions import ClientError
from services import bedrock_utils


class FakeBedrockClient:
    def __init__(self):
        self.calls = []

    def invoke_model(self, **kwargs):
        self.calls.append(kwargs)
        body = {"outputText": "Summary text"}
        return {"body": BytesIO(json.dumps(body).encode("utf-8"))}


def test_summarize_transcript_uses_bedrock_response():
    client = FakeBedrockClient()
    result = bedrock_utils.summarize_transcript("mtg-1", "hello", client=client)
    assert result["summary"] == "Summary text"
    assert client.calls
    assert client.calls[0]["modelId"]


def test_create_embedding_fallback_on_error():
    class ErrorClient:
        def invoke_model(self, **kwargs):
            raise ClientError({"Error": {"Code": "Boom", "Message": "fail"}}, "InvokeModel")

    vector = bedrock_utils.create_embedding("hello", client=ErrorClient())
    assert len(vector) == 16


def test_extract_keywords_prefers_bedrock_json():
    class KeywordClient:
        def invoke_model(self, **kwargs):
            body = {"keywords": ["議題整理", "次のアクション"]}
            return {"body": BytesIO(json.dumps(body).encode("utf-8"))}

    keywords = bedrock_utils.extract_keywords("議題をまとめます", client=KeywordClient())
    assert keywords == ["議題整理", "次のアクション"]


def test_extract_keywords_fallback_on_error():
    class ErrorClient:
        def invoke_model(self, **kwargs):
            raise ClientError({"Error": {"Code": "Boom", "Message": "fail"}}, "InvokeModel")

    keywords = bedrock_utils.extract_keywords("見積り 調整 共有", client=ErrorClient(), max_keywords=2)
    assert keywords == ["見積り", "調整"]
