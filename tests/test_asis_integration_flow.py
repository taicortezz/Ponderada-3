import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from asis_integration_flow import (
    API_PROTOCOL,
    API_VERSION,
    STATUS_ENDPOINT,
    UPLOAD_ENDPOINT,
    RESULT_ENDPOINT,
    ASISIntegrationFlow,
    AuthenticationError,
    IntegrationTimeoutError,
    ProcessNotFoundError,
)


class FakeClock:
    def __init__(self, values):
        self.values = iter(values)

    def __call__(self):
        return next(self.values)


class SequenceTransport:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def __call__(self, method, path, headers, body):
        self.calls.append({"method": method, "path": path, "headers": headers, "body": body})
        current = self.responses.pop(0)
        if isinstance(current, Exception):
            raise current
        return current


class ASISIntegrationFlowTests(unittest.TestCase):
    def test_run_flow_success_with_protocol_version_and_endpoints(self):
        transport = SequenceTransport(
            [
                {"status_code": 202, "data": {"process_id": "proc-1"}},
                {"status_code": 200, "data": {"status": "completed"}},
                {"status_code": 200, "data": {"result": {"documento": "ok"}}},
            ]
        )
        clock = FakeClock([0, 1, 1, 2, 2, 3])
        flow = ASISIntegrationFlow(transport, "acc", "app", clock=clock)

        result = flow.run_flow("arquivo.txt", "conteudo fiscal")

        self.assertEqual(result["final_status"], "completed")
        self.assertEqual(result["protocol"], API_PROTOCOL)
        self.assertEqual(result["version"], API_VERSION)
        self.assertEqual(result["process_id"], "proc-1")
        self.assertEqual(transport.calls[0]["method"], "POST")
        self.assertEqual(transport.calls[0]["path"], UPLOAD_ENDPOINT)
        self.assertEqual(transport.calls[1]["path"], STATUS_ENDPOINT.format(process_id="proc-1"))
        self.assertEqual(transport.calls[2]["path"], RESULT_ENDPOINT.format(process_id="proc-1"))
        self.assertEqual(transport.calls[0]["headers"]["account-key"], "acc")
        self.assertEqual(transport.calls[0]["headers"]["app-key"], "app")
        self.assertLessEqual(result["upload_time_s"], 5.0)
        self.assertLessEqual(result["result_time_s"], 5.0)

    def test_run_flow_tolerates_one_transient_failure_in_polling(self):
        transport = SequenceTransport(
            [
                {"status_code": 202, "data": {"process_id": "proc-2"}},
                {"status_code": 200, "data": {"status": "temporary_failure"}},
                {"status_code": 200, "data": {"status": "processing"}},
                {"status_code": 200, "data": {"status": "completed"}},
                {"status_code": 200, "data": {"result": {"documento": "ok"}}},
            ]
        )
        clock = FakeClock([0, 1, 1, 2, 2, 3, 3, 4, 4, 5])
        flow = ASISIntegrationFlow(transport, "acc", "app", clock=clock)

        result = flow.run_flow("arquivo.txt", "conteudo fiscal")

        self.assertEqual(result["transient_failures"], 1)
        self.assertEqual(result["status_checks"], 3)

    def test_upload_raises_authentication_error(self):
        transport = SequenceTransport([{"status_code": 401, "data": {}}])
        clock = FakeClock([0, 1])
        flow = ASISIntegrationFlow(transport, "acc", "app", clock=clock)

        with self.assertRaises(AuthenticationError):
            flow.upload_file("arquivo.txt", "conteudo fiscal")

    def test_status_raises_process_not_found(self):
        transport = SequenceTransport([{"status_code": 404, "data": {}}])
        clock = FakeClock([0, 1])
        flow = ASISIntegrationFlow(transport, "acc", "app", clock=clock)

        with self.assertRaises(ProcessNotFoundError):
            flow.get_process_status("proc-inexistente")

    def test_upload_raises_timeout_when_sla_is_exceeded(self):
        transport = SequenceTransport([{"status_code": 202, "data": {"process_id": "proc-3"}}])
        clock = FakeClock([0, 6])
        flow = ASISIntegrationFlow(transport, "acc", "app", clock=clock)

        with self.assertRaises(IntegrationTimeoutError):
            flow.upload_file("arquivo.txt", "conteudo fiscal")


if __name__ == "__main__":
    unittest.main()
