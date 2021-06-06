#!/usr/bin/env python
# encoding: utf-8
# Copyright 2016-2021 Alexander Mollberg
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
from http.server import BaseHTTPRequestHandler, HTTPServer


class HtmlHandler(BaseHTTPRequestHandler):
  def do_GET(self):
    if self.path not in ['', '/']:
      self.send_response(404)
      return
    html = self.server.html_callback()
    self.send_response(200)
    self.send_header('Content-type', 'text/html')
    self.end_headers()
    self.wfile.write(str.encode(html))


def start_server(html_callback):
  # Port 0 means select an arbitrary unused port
  port = 0
  server = HTTPServer(('127.0.0.1', port), HtmlHandler)
  server.html_callback = html_callback

  def serve_requests():
    server.serve_forever()

  import threading
  threading.Thread(target=serve_requests).start()
  return server
