#!/usr/bin/env python

from BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer

class HtmlHandler(BaseHTTPRequestHandler):
  def do_GET(self):
    if self.path not in ['', '/']:
      self.send_response(404)
      return
    html = self.server.html_callback()
    self.send_response(200)
    self.send_header('Content-type', 'text/html')
    self.end_headers()
    self.wfile.write(html)

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
