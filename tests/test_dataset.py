from backend.dataset import validate_dev_dataset
from backend.models import Conversation, Utterance


def make_record(i: int, language: str, channel: str) -> Conversation:
    return Conversation(
        conversation_id=f"c-{i}",
        channel=channel,
        language=language,
        transcript=[
            Utterance(timestamp="00:00:01", speaker="client", text="test"),
            Utterance(timestamp="00:00:02", speaker="agent", text="reply"),
        ],
        audio_url="https://example.com/audio.mp3" if channel == "voice_call" else None,
    )


def test_expected_dev_distribution():
    records = []
    index = 0
    for language, count in [("RU", 35), ("KZ", 15), ("EN", 15)]:
        for _ in range(count):
            channel = "voice_call" if index >= 60 else "agent_chat"
            records.append(make_record(index, language, channel))
            index += 1

    result = validate_dev_dataset(records)
    assert result["valid"] is True
    assert result["total"] == 65
