import json
from pathlib import Path
import unittest

from models import DevelopmentEvent
from services.analysis_service import analyze
from services.privacy_service import sanitize_checkpoint


class PrivacyBoundaryTests(unittest.TestCase):
    def test_redacted_checkpoint_never_retains_raw_prompt_or_transcript(self):
        fixture = Path(__file__).parent / "fixtures" / "redacted_checkpoint.json"
        checkpoint = sanitize_checkpoint(json.loads(fixture.read_text(encoding="utf-8")))

        self.assertEqual("redacted", checkpoint["context_completeness"])
        self.assertNotIn("prompt", checkpoint)
        self.assertNotIn("transcript", checkpoint)
        self.assertIn("prompt", checkpoint["redacted_fields"])
        self.assertIn("transcript", checkpoint["redacted_fields"])
        self.assertEqual("Investigate authentication latency", checkpoint["intent"])

    def test_prompt_and_transcript_aliases_are_also_removed(self):
        checkpoint = sanitize_checkpoint({"user_prompt_text": "private", "agent_transcript_v2": "private", "intent": "Safe"})

        self.assertEqual("redacted", checkpoint["context_completeness"])
        self.assertNotIn("user_prompt_text", checkpoint)
        self.assertNotIn("agent_transcript_v2", checkpoint)
        self.assertEqual("Safe", checkpoint["intent"])

    def test_missing_checkpoint_is_explicitly_unavailable(self):
        checkpoint = sanitize_checkpoint(None)

        self.assertEqual("unavailable", checkpoint["context_completeness"])
        self.assertEqual([], checkpoint["redacted_fields"])

    def test_redacted_context_cannot_be_release_ready(self):
        event = DevelopmentEvent(
            event_id="evt-redacted", project_id="project-1", checkpoint_id="cp-redacted",
            timestamp="2026-09-06T00:00:00Z", intent="Improve latency",
            git_evidence={"available": True, "changed_files": []},
            metadata={"context_completeness": "redacted", "redacted_fields": ["prompt"]},
        )

        intelligence = analyze(event)

        self.assertEqual("Not ready", intelligence.release_readiness)
        self.assertEqual("Needs context", intelligence.handoff_readiness)
        self.assertTrue(any("redacted" in gap for gap in intelligence.smart_checkpoint_gaps))


if __name__ == "__main__":
    unittest.main()
