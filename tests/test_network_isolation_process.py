"""Real socket/DNS/HTTP rejection and loopback service in a fresh process."""
import json
import os
import subprocess
import sys


def test_fresh_process_blocks_external_and_preserves_loopback(tmp_path):
    script = r'''
import json, socket, sys, threading, urllib.request
from http.server import BaseHTTPRequestHandler
from socketserver import TCPServer
attempts = []
def observe(event, args):
    if event.startswith('socket.') and event in ('socket.connect', 'socket.getaddrinfo'):
        attempts.append([event, repr(args)[0:180]])
sys.addaudithook(observe)
from cursiv_v215.core import netgate
netgate.set_offline(True)
blocked = []
for label, action in [
    ('socket', lambda: socket.create_connection(('203.0.113.1', 443), timeout=.1)),
    ('dns', lambda: socket.getaddrinfo('example.invalid', 443)),
    ('http', lambda: urllib.request.build_opener(urllib.request.ProxyHandler({})).open('https://example.invalid/', timeout=.1)),
]:
    try:
        action()
    except OSError:
        blocked.append(label)
    else:
        raise AssertionError('External request was not blocked: ' + label)
class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200); self.end_headers(); self.wfile.write(b'local fixture')
    def log_message(self, *a): pass
server = TCPServer(('127.0.0.1', 0), Handler)  # no HTTPServer reverse-DNS lookup
thread = threading.Thread(target=server.serve_forever, daemon=True); thread.start()
try:
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    with opener.open('http://127.0.0.1:%s/' % server.server_address[1], timeout=2) as response:
        assert response.read() == b'local fixture'
finally:
    server.shutdown(); server.server_close(); thread.join(2)
netgate.set_offline(False); assert netgate.allowed()
netgate.set_offline(True); assert not netgate.allowed()
print(json.dumps(dict(blocked=blocked, attempts=attempts, loopback=True)))
'''
    env = dict(os.environ, CURSIV_APP_DATA=str(tmp_path / 'data'),
               HOME=str(tmp_path / 'home'), USERPROFILE=str(tmp_path / 'home'))
    result = subprocess.run([sys.executable, '-B', '-c', script], env=env,
                            capture_output=True, text=True, timeout=20)
    assert result.returncode == 0, result.stderr
    record = json.loads(result.stdout.strip().splitlines()[-1])
    assert record['blocked'] == ['socket', 'dns', 'http'] and record['loopback']
    assert any('203.0.113.1' in row[1] for row in record['attempts'])
