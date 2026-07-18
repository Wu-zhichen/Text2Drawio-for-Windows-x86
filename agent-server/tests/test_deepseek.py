import json
import unittest
from unittest.mock import patch

from app.agent.deepseek import DeepSeekClient, DeepSeekError, _parse_json_object


class _FakeResponse:
    def __init__(self, payload: bytes) -> None:
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, *_args) -> None:
        return None

    def read(self) -> bytes:
        return self.payload


def _api_response(content: str, finish_reason: str = "stop") -> bytes:
    return json.dumps(
        {
            "choices": [
                {"message": {"content": content}, "finish_reason": finish_reason}
            ]
        }
    ).encode("utf-8")


class DeepSeekClientTests(unittest.TestCase):
    def test_parser_accepts_fence_and_short_preface(self) -> None:
        self.assertEqual(_parse_json_object("```json\n{\"ok\": true}\n```"), {"ok": True})
        self.assertEqual(_parse_json_object("Result: {\"ok\": true}\nDone"), {"ok": True})

    @patch("app.agent.deepseek.time.sleep", return_value=None)
    @patch("app.agent.deepseek.urllib.request.urlopen")
    def test_empty_content_is_retried(self, mocked_open, _mocked_sleep) -> None:
        mocked_open.side_effect = [
            _FakeResponse(_api_response("")),
            _FakeResponse(_api_response('{"ok": true}')),
        ]
        client = DeepSeekClient(
            api_key="test", model="test", base_url="https://example.invalid", max_retries=1
        )
        result = client._request("return json", "request", 1024)
        self.assertEqual(result, {"ok": True})
        self.assertEqual(mocked_open.call_count, 2)

    @patch("app.agent.deepseek.urllib.request.urlopen")
    def test_truncation_has_specific_error(self, mocked_open) -> None:
        mocked_open.return_value = _FakeResponse(
            _api_response('{"nodes":[', finish_reason="length")
        )
        client = DeepSeekClient(
            api_key="test", model="test", base_url="https://example.invalid", max_retries=0
        )
        with self.assertRaisesRegex(DeepSeekError, "truncated"):
            client._request("return json", "request", 1024)


if __name__ == "__main__":
    unittest.main()
