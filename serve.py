"""本地预览服务器：给 .js/.webmanifest 正确的 MIME，避免 Windows 注册表把 .js 认成 text/plain。

用法：  py serve.py [端口]     默认 http://127.0.0.1:8765
"""
import functools
import http.server
import socketserver
import sys

PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8765


class Handler(http.server.SimpleHTTPRequestHandler):
    extensions_map = {
        **http.server.SimpleHTTPRequestHandler.extensions_map,
        ".js": "text/javascript",
        ".mjs": "text/javascript",
        ".webmanifest": "application/manifest+json",
        ".woff2": "font/woff2",
        ".svg": "image/svg+xml",
        ".json": "application/json",
        ".css": "text/css",
        ".html": "text/html",
    }

    def end_headers(self):
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def log_message(self, fmt, *args):  # 安静一点
        sys.stderr.write("%s - %s\n" % (self.address_string(), fmt % args))


socketserver.TCPServer.allow_reuse_address = True
with socketserver.TCPServer(("127.0.0.1", PORT), functools.partial(Handler, directory=str(__import__("pathlib").Path(__file__).parent))) as httpd:
    print(f"归岸 · 本地预览  http://127.0.0.1:{PORT}/index.html")
    httpd.serve_forever()
