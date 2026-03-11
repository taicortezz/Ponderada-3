import time

API_PROTOCOL = "HTTPS/REST"
API_VERSION = "v1"
UPLOAD_ENDPOINT = f"/api/{API_VERSION}/upload"
STATUS_ENDPOINT = f"/api/{API_VERSION}/processo/{{process_id}}"
RESULT_ENDPOINT = f"/api/{API_VERSION}/resultado/processo/{{process_id}}"
UPLOAD_SLA_SECONDS = 5.0
STATUS_SLA_SECONDS = 5.0
MAX_TRANSIENT_FAILURES = 4
MAX_STATUS_CHECKS = 6


class IntegrationError(Exception):
    pass


class AuthenticationError(IntegrationError):
    pass


class ProcessNotFoundError(IntegrationError):
    pass


class IntegrationTimeoutError(IntegrationError):
    pass


class TransientStatusError(IntegrationError):
    pass


class ASISIntegrationFlow:
    def __init__(self, transport, account_key, app_key, clock=None):
        self.transport = transport
        self.account_key = account_key
        self.app_key = app_key
        self.clock = clock or time.perf_counter

    def _headers(self):
        return {"account-key": self.account_key, "app-key": self.app_key}

    def _request(self, method, path, body, sla_seconds):
        start = self.clock()
        try:
            response = self.transport(method, path, self._headers(), body)
        except TimeoutError as exc:
            raise IntegrationTimeoutError("Tempo limite excedido na integração.") from exc

        elapsed = self.clock() - start
        if elapsed > sla_seconds:
            raise IntegrationTimeoutError("Tempo de resposta acima do SLA da integração.")

        status_code = response["status_code"]
        data = response.get("data", {})

        if status_code == 401:
            raise AuthenticationError("Falha de autenticação na API ASIS.")
        if status_code == 404:
            raise ProcessNotFoundError("Processo não encontrado.")
        if status_code >= 500:
            raise IntegrationError("Falha no serviço de processamento fiscal.")

        return data, round(elapsed, 3)

    def upload_file(self, file_name, content):
        data, elapsed = self._request(
            "POST",
            UPLOAD_ENDPOINT,
            {"file_name": file_name, "content": content},
            UPLOAD_SLA_SECONDS,
        )
        process_id = data.get("process_id")
        if not process_id:
            raise IntegrationError("Resposta de upload sem identificador do processo.")
        return {"process_id": process_id, "response_time_s": elapsed, "protocol": API_PROTOCOL, "version": API_VERSION}

    def get_process_status(self, process_id):
        data, elapsed = self._request(
            "GET",
            STATUS_ENDPOINT.format(process_id=process_id),
            None,
            STATUS_SLA_SECONDS,
        )
        status = data.get("status")
        if status == "temporary_failure":
            raise TransientStatusError("Falha transitória na consulta do status.")
        return {"status": status, "response_time_s": elapsed, "protocol": API_PROTOCOL, "version": API_VERSION}

    def get_process_result(self, process_id):
        data, elapsed = self._request(
            "GET",
            RESULT_ENDPOINT.format(process_id=process_id),
            None,
            STATUS_SLA_SECONDS,
        )
        return {"result": data.get("result"), "response_time_s": elapsed, "protocol": API_PROTOCOL, "version": API_VERSION}

    def run_flow(self, file_name, content):
        upload = self.upload_file(file_name, content)
        transient_failures = 0

        for status_checks in range(1, MAX_STATUS_CHECKS + 1):
            try:
                status_data = self.get_process_status(upload["process_id"])
            except TransientStatusError:
                transient_failures += 1
                if transient_failures > MAX_TRANSIENT_FAILURES:
                    raise IntegrationError("Número máximo de falhas transitórias excedido.")
                continue

            status = status_data["status"]
            if status == "completed":
                result = self.get_process_result(upload["process_id"])
                return {
                    "process_id": upload["process_id"],
                    "final_status": status,
                    "status_checks": status_checks,
                    "transient_failures": transient_failures,
                    "protocol": API_PROTOCOL,
                    "version": API_VERSION,
                    "upload_time_s": upload["response_time_s"],
                    "result_time_s": result["response_time_s"],
                    "result": result["result"],
                }
            if status not in {"queued", "processing"}:
                raise IntegrationError("Status inválido retornado pela integração.")

        raise IntegrationError("Processo não concluído dentro do limite de consultas.")
