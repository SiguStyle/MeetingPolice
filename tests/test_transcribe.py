import pytest
from botocore.exceptions import ClientError

from services.transcribe_stream import TranscribeStream


class FakeTranscribeClient:
    def __init__(self):
        self.kwargs = None

    def start_stream_transcription(self, **kwargs):
        self.kwargs = kwargs
        return {"SessionId": "session-123"}


@pytest.mark.asyncio
async def test_transcribe_stream_invokes_client():
    client = FakeTranscribeClient()
    stream = TranscribeStream(client=client)
    session_id = await stream.start([b"abc"])
    assert session_id == "session-123"
    assert client.kwargs["LanguageCode"] == "en-US"


@pytest.mark.asyncio
async def test_transcribe_stream_handles_error():
    class ErrorClient:
        def start_stream_transcription(self, **kwargs):
            raise ClientError({"Error": {"Code": "Boom", "Message": "fail"}}, "StartStreamTranscription")

    stream = TranscribeStream(client=ErrorClient())
    message = await stream.start([b"abc"])
    assert message.startswith("error:")
