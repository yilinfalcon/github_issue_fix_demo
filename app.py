import json
import logging
import os
import urllib.request
import urllib.parse
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

    def _write_html(self, status: HTTPStatus, html: str) -> None:
        body = html.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
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
                    "endpoints": ["/health", "/api/echo?message=hello", "/counter", "/location"],
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

        if parsed.path == "/api/reverse-geocode":
            params = parse_qs(parsed.query)
            try:
                lat = float(params.get("lat", [None])[0])
                lon = float(params.get("lon", [None])[0])
            except (ValueError, TypeError, IndexError):
                self._write_json(
                    HTTPStatus.BAD_REQUEST,
                    {"error": "invalid_coordinates", "message": "lat and lon parameters required"},
                )
                return

            try:
                url = (
                    "https://nominatim.openstreetmap.org/reverse"
                    f"?format=json&lat={lat}&lon={lon}&zoom=10&addressdetails=1&accept-language=en"
                )
                req = urllib.request.Request(url, headers={"User-Agent": APP_NAME})
                with urllib.request.urlopen(req, timeout=5) as response:
                    data = json.loads(response.read().decode("utf-8"))
                    address = data.get("address", {})
                    
                    location_parts = []
                    if address.get("city"):
                        location_parts.append(address["city"])
                    elif address.get("town"):
                        location_parts.append(address["town"])
                    elif address.get("village"):
                        location_parts.append(address["village"])
                    
                    if address.get("state"):
                        location_parts.append(address["state"])
                    if address.get("country"):
                        location_parts.append(address["country"])
                    
                    location = ", ".join(location_parts) if location_parts else data.get("display_name", "未知位置")
                    
                    self._write_json(
                        HTTPStatus.OK,
                        {
                            "lat": round(lat, 3),
                            "lon": round(lon, 3),
                            "location": location,
                            "display_name": data.get("display_name", ""),
                        },
                    )
            except Exception as e:
                LOGGER.warning("reverse_geocode_error | lat=%s | lon=%s | error=%s", lat, lon, str(e))
                self._write_json(
                    HTTPStatus.INTERNAL_SERVER_ERROR,
                    {"error": "geocoding_failed", "message": str(e)},
                )
            return

        if parsed.path == "/counter":
            html = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>数字累加器</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            display: flex;
            justify-content: center;
            align-items: center;
            min-height: 100vh;
        }
        #counter {
            font-size: 120px;
            font-weight: bold;
            color: black;
            user-select: none;
        }
    </style>
</head>
<body>
    <div id="counter">0</div>
    <script>
        let count = 0;
        const counterElement = document.getElementById('counter');
        
        function updateCounter() {
            count += 1;
            counterElement.textContent = count;
        }
        
        setInterval(updateCounter, 1000);
    </script>
</body>
</html>"""
            self._write_html(HTTPStatus.OK, html)
            return

        if parsed.path == "/location":
            html = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>地理位置</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            display: flex;
            justify-content: center;
            align-items: center;
            min-height: 100vh;
            padding: 20px;
        }
        .container {
            text-align: center;
            max-width: 600px;
        }
        h1 {
            font-size: 32px;
            margin-bottom: 30px;
            color: #333;
        }
        .info-item {
            margin: 20px 0;
            padding: 15px;
            background: #f5f5f5;
            border-radius: 8px;
        }
        .label {
            font-size: 14px;
            color: #666;
            margin-bottom: 5px;
        }
        .value {
            font-size: 18px;
            color: #333;
            font-weight: 500;
        }
        .loading {
            color: #999;
            font-style: italic;
        }
        .error {
            color: #d32f2f;
            background: #ffebee;
            padding: 15px;
            border-radius: 8px;
            margin-top: 20px;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>当前位置信息</h1>
        <div class="info-item">
            <div class="label">纬度 (Latitude)</div>
            <div class="value" id="lat" class="loading">获取中...</div>
        </div>
        <div class="info-item">
            <div class="label">经度 (Longitude)</div>
            <div class="value" id="lon" class="loading">获取中...</div>
        </div>
        <div class="info-item">
            <div class="label">区域位置</div>
            <div class="value" id="location" class="loading">获取中...</div>
        </div>
        <div id="error" style="display: none;"></div>
    </div>
    <script>
        const latElement = document.getElementById('lat');
        const lonElement = document.getElementById('lon');
        const locationElement = document.getElementById('location');
        const errorElement = document.getElementById('error');

        function showError(message) {
            errorElement.textContent = message;
            errorElement.style.display = 'block';
            latElement.textContent = '获取失败';
            lonElement.textContent = '获取失败';
            locationElement.textContent = '获取失败';
        }

        function updateLocation(lat, lon, location) {
            latElement.textContent = lat.toFixed(3);
            lonElement.textContent = lon.toFixed(3);
            locationElement.textContent = location || '未知位置';
        }

        if (navigator.geolocation) {
            navigator.geolocation.getCurrentPosition(
                function(position) {
                    const lat = position.coords.latitude;
                    const lon = position.coords.longitude;
                    
                    latElement.textContent = lat.toFixed(3);
                    lonElement.textContent = lon.toFixed(3);
                    locationElement.textContent = '查询中...';

                    fetch(`/api/reverse-geocode?lat=${lat}&lon=${lon}`)
                        .then(response => response.json())
                        .then(data => {
                            if (data.error) {
                                showError('获取区域位置失败: ' + data.message);
                            } else {
                                updateLocation(lat, lon, data.location);
                            }
                        })
                        .catch(error => {
                            showError('网络错误: ' + error.message);
                        });
                },
                function(error) {
                    let errorMsg = '获取地理位置失败: ';
                    switch(error.code) {
                        case error.PERMISSION_DENIED:
                            errorMsg += '用户拒绝了地理位置请求';
                            break;
                        case error.POSITION_UNAVAILABLE:
                            errorMsg += '位置信息不可用';
                            break;
                        case error.TIMEOUT:
                            errorMsg += '请求超时';
                            break;
                        default:
                            errorMsg += '未知错误';
                            break;
                    }
                    showError(errorMsg);
                },
                {
                    enableHighAccuracy: true,
                    timeout: 10000,
                    maximumAge: 0
                }
            );
        } else {
            showError('您的浏览器不支持地理位置功能');
        }
    </script>
</body>
</html>"""
            self._write_html(HTTPStatus.OK, html)
            return

        self._write_json(
            HTTPStatus.OK,
            {
                "service": APP_NAME,
                "endpoints": ["/health", "/api/echo?message=hello", "/counter", "/location"],
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
