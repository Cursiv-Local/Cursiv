"""Optional fleet endpoint configuration, read once without starting network work."""
import os

RELAY_URL = os.environ.get('CURSIV_RELAY_URL', '').rstrip('/')
FLEET_TOKEN = os.environ.get('CURSIV_FLEET_TOKEN', '')
