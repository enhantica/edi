"""Serve the unpacked web app with the headers required by its threaded kit."""

import functools
import http.server
import sys


class Handler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header('Cross-Origin-Opener-Policy', 'same-origin')
        self.send_header('Cross-Origin-Embedder-Policy', 'require-corp')
        super().end_headers()


if __name__ == '__main__':
    http.server.ThreadingHTTPServer(
        ('127.0.0.1', int(sys.argv[2])), functools.partial(Handler, directory=sys.argv[1])
    ).serve_forever()
