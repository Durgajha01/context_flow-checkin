import unittest
from unittest.mock import patch
from services import databricks_service

class DatabricksBoundaryTests(unittest.TestCase):
    def test_checkpoint_sent_to_sink_is_sanitized(self):
        with patch("services.databricks_service._write_remote") as remote:
            databricks_service.store_event({"event_id":"e","project_id":"p","checkpoint_id":"c","timestamp":"now"},{"checkpoint_id":"c","project_id":"p","prompt":"secret","transcript":"secret"},[],[])
        checkpoint=[call.args[1] for call in remote.call_args_list if call.args[0]=="checkpoint"][0]
        self.assertNotIn("prompt",checkpoint); self.assertNotIn("transcript",checkpoint); self.assertEqual("redacted",checkpoint["context_completeness"])
