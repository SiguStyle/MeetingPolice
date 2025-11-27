from __future__ import annotations

from botocore.exceptions import BotoCoreError, ClientError

from backend.config import get_settings
from backend.utils.auth_aws import get_session


def analyze_sentiment(text: str) -> dict:
    session = get_session()
    client = session.client("comprehend", region_name=get_settings().aws_region)
    try:
        response = client.detect_sentiment(Text=text, LanguageCode=get_settings().comprehend_language)
        return response
    except (BotoCoreError, ClientError):
        return {"Sentiment": "NEUTRAL", "SentimentScore": {"Positive": 0.3, "Negative": 0.2, "Neutral": 0.5, "Mixed": 0.0}}
