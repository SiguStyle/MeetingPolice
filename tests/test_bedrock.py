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


def test_classify_transcript_segments_uses_response():
    class ClassifyClient:
        def invoke_model(self, **kwargs):
            body = {
                "classifications": [
                    {"index": 1, "category": "報告"},
                    {"index": 2, "category": "決定"},
                ]
            }
            return {"body": BytesIO(json.dumps(body).encode("utf-8"))}

    inputs = [
        {"index": 1, "speaker": "A", "text": "進捗を共有します"},
        {"index": 2, "speaker": "B", "text": "この内容で決定します"},
    ]
    results = bedrock_utils.classify_transcript_segments(inputs, client=ClassifyClient())
    assert [item["category"] for item in results] == ["報告", "決定"]


def test_classify_transcript_segments_returns_empty_on_error():
    class ErrorClient:
        def invoke_model(self, **kwargs):
            raise ClientError({"Error": {"Code": "Boom", "Message": "fail"}}, "InvokeModel")

    inputs = [
        {"index": 1, "speaker": "A", "text": "次の議題に移りましょう"},
        {"index": 2, "speaker": "B", "text": "雑談ですが週末はどうでしたか"},
    ]
    results = bedrock_utils.classify_transcript_segments(inputs, client=ErrorClient())
    assert results == []
