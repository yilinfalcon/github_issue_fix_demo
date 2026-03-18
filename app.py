import json
import logging
import os
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from logging.handlers import RotatingFileHandler
from pathlib import Path
from urllib.parse import parse_qs, urlparse


APP_NAME = "github-issue-fix-agent-demo"
LOG_DIR = Path(__file__).resolve().parent / "logs"
LOG_FILE = LOG_DIR / "app.log"


def configure_logging() -> logging.Logger:
    LOG_DIR.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger(APP_NAME)
    logger.setLevel(logging.INFO)
    logger.handlers.clear()

    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
    )

    file_handler = RotatingFileHandler(LOG_FILE, maxBytes=512 * 1024, backupCount=3)
    file_handler.setFormatter(formatter)

    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)

    logger.addHandler(file_handler)
    logger.addHandler(stream_handler)
    logger.propagate = False
    return logger


LOGGER = configure_logging()


class DemoHandler(BaseHTTPRequestHandler):
    server_version = "IssueFixAgentDemo/0.1"

    def log_message(self, format: str, *args) -> None:
        LOGGER.info(
            "request | client=%s | method=%s | path=%s | detail=%s",
            self.client_address[0],
            self.command,
            self.path,
            format % args,
        )

    def _write_json(self, status: HTTPStatus, payload: dict) -> None:
        body = json.dumps(payload, ensure_ascii=True).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        parsed = urlparse(self.path)

        if parsed.path == "/":
            self._write_json(
                HTTPStatus.OK,
                {
                    "service": APP_NAME,
                    "endpoints": ["/health", "/api/echo?message=hello"],
                },
            )
            return

        if parsed.path == "/health":
            self._write_json(
                HTTPStatus.OK,
                {
                    "status": "ok",
                    "service": APP_NAME,
                },
            )
            return

        if parsed.path == "/api/echo":
            params = parse_qs(parsed.query)
            message = params.get("message", ["hello"])[0]
            self._write_json(
                HTTPStatus.OK,
                {
                    "message": message,
                    "service": APP_NAME,
                },
            )
            return

        self._write_json(
            HTTPStatus.OK,
            {
                "service": APP_NAME,
                "endpoints": ["/health", "/api/echo?message=hello"],
            },
        )

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path != "/api/echo":
            self._write_json(
                HTTPStatus.NOT_FOUND,
                {"error": "not_found", "path": parsed.path},
            )
            return

        content_length = int(self.headers.get("Content-Length", "0"))
        raw_body = self.rfile.read(content_length) if content_length > 0 else b"{}"

        try:
            payload = json.loads(raw_body.decode("utf-8"))
        except json.JSONDecodeError:
            LOGGER.warning("invalid_json | path=%s | body=%r", parsed.path, raw_body)
            self._write_json(
                HTTPStatus.BAD_REQUEST,
                {"error": "invalid_json"},
            )
            return

        message = payload.get("message", "hello")
        LOGGER.info("echo_payload | message=%s", message)
        self._write_json(
            HTTPStatus.OK,
            {
                "message": message,
                "method": "POST",
                "service": APP_NAME,
            },
        )


def run() -> None:
    host = os.getenv("DEMO_HOST", "127.0.0.1")
    port = int(os.getenv("DEMO_PORT", "8000"))

    server = ThreadingHTTPServer((host, port), DemoHandler)
    LOGGER.info("server_start | host=%s | port=%s | log_file=%s", host, port, LOG_FILE)

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        LOGGER.info("server_stop | reason=keyboard_interrupt")
    finally:
        server.server_close()


if __name__ == "__main__":
    run()
