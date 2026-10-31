"""Intentional deny tests: every operation is blocked before the OS/network."""
import socket
import subprocess
import sys
import pytest
import os
if not os.environ.get('CURSIV_STRICT_GUARD'):
    pytest.skip('Run with scripts/offline_validate.py',allow_module_level=True)
import offline_guard as guard

@pytest.mark.parametrize('operation',[
 lambda:socket.getaddrinfo('example.invalid',443),
 lambda:socket.socket().connect(('127.0.0.1',11434)),
 lambda:socket.socket().bind(('127.0.0.1',0)),
 lambda:socket.socket(socket.AF_INET,socket.SOCK_DGRAM).sendto(b'fixture',('203.0.113.1',9)),
 lambda:subprocess.run(['ollama','list']),
 lambda:subprocess.run([sys.executable,'-I','-c','raise AssertionError("must not execute")']),
])
def test_guard_denies_before_network_or_process(operation):
    with guard.expected_denial(),pytest.raises(guard.OfflineViolation):operation()


def test_python_child_inherits_guard():
    output=subprocess.check_output([sys.executable,'-c','import offline_guard; print(offline_guard._installed)'],text=True)
    assert output.strip()=='True'
