"""
Cursiv Field Station: Cursiv's engine served to phones, tablets and laptops from a Raspberry Pi 5
over its own Wi-Fi (docs/FIELD-STATION-PLAN.md). The desktop app doesn't use this package.

    python -m cursiv_engine.station [--host 127.0.0.1] [--port 8080] [--simulate A]

Modules: telemetry (hardware readings, each labelled real / derived / simulated / unavailable),
simulation (named test scenarios), storage (drives by filesystem id), sessions (sign-in, CSRF,
rate limits), server (the local web server and API), web/ (the browser interface).
"""
