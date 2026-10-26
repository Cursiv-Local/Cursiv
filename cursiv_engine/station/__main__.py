"""
Start the Field Station server:

    python -m cursiv_engine.station [--host 127.0.0.1] [--port 8080] [--simulate A] [--shutdown-command ...]

--host defaults to this computer only. On the Raspberry Pi the service binds the station's Wi-Fi address
(phase 6/7); clients outside private networks are refused either way. Offline mode is turned on, so nothing
connects out. The data lease is held for the server's whole life, as the desktop app does, so no other
Cursiv process can write the same data at the same time.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="cursiv-station")
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=8080)
    ap.add_argument("--simulate", help="a hardware scenario A-F for development (labelled SIMULATED everywhere)")
    ap.add_argument("--shutdown-command", nargs="+",
                    help="what the Shut down button runs after a safe stop, e.g. sudo -n /usr/bin/systemctl poweroff")
    ap.add_argument("--hostname", action="append", default=[], help="another name this station answers to")
    args = ap.parse_args(argv)

    from cursiv_engine.core import netgate
    from cursiv_engine.core.data_lease import DataLease
    from cursiv_engine.core.phone_receive import lan_addresses
    from cursiv_engine.station import simulation, server

    netgate.install()
    netgate.set_offline(True)
    simulation.activate(args.simulate.upper() if args.simulate else None)
    lease = DataLease()
    lease.__enter__()
    lease.hold_until_exit()

    home = Path.home() / ".cursiv"
    station = server.Station(hosts=set(args.hostname) | set(lan_addresses()),
                             data_paths={"internal": home}, shutdown_command=args.shutdown_command,
                             exports=home / "fieldlog" / "exports")
    httpd = server.serve(station, args.host, args.port)
    print(f"Cursiv Field Station on http://{args.host}:{httpd.server_address[1]}/ "
          f"(also http://cursiv.local:{httpd.server_address[1]}/ where name lookup works)", flush=True)
    if args.simulate:
        print(f"SIMULATED hardware: scenario {simulation.active()}. No reading is real.", flush=True)
    if station.gate.needs_setup():
        print(f"First-run setup code: {station.gate.setup_code}  (type it on the setup page)", flush=True)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        station.shut_down()
    finally:
        httpd.server_close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
