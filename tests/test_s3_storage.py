import io
import json

import boto3
from botocore.stub import Stubber, ANY
from botocore.exceptions import ClientError
from botocore.response import StreamingBody

from services.s3_storage import S3Storage


def test_s3_storage_write_json_uses_client(tmp_path):
    client = boto3.client("s3", region_name="us-east-1")
    stubber = Stubber(client)
    stubber.add_response(
        "put_object",
        {},
        {
            "Bucket": "test-bucket",
            "Key": "summaries/demo.json",
            "Body": ANY,
            "ContentType": "application/json",
        },
    )
    stubber.activate()

    storage = S3Storage(bucket="test-bucket", client=client)
    storage._fallback_dir = tmp_path
    storage.write_json("summaries/demo.json", {"hello": "world"})
    stubber.assert_no_pending_responses()


def test_s3_storage_read_text_fallback(tmp_path):
    class ErrorClient:
        def get_object(self, **kwargs):
            raise ClientError({"Error": {"Code": "404", "Message": "missing"}}, "GetObject")

        def get_paginator(self, name):
            raise ClientError({"Error": {"Code": "404", "Message": "missing"}}, "ListObjectsV2")

        def put_object(self, **kwargs):
            raise ClientError({"Error": {"Code": "500", "Message": "fail"}}, "PutObject")

    storage = S3Storage(bucket="test-bucket", client=ErrorClient())
    storage._fallback_dir = tmp_path
    path = tmp_path / "transcripts"
    path.mkdir(parents=True, exist_ok=True)
    file_path = path / "demo.txt"
    file_path.write_text("local copy", encoding="utf-8")

    assert storage.read_text("transcripts/demo.txt") == "local copy"
