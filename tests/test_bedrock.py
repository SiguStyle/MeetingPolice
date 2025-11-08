import json
from io import BytesIO

from services import bedrock_utils
from botocore.exceptions import ClientError


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
