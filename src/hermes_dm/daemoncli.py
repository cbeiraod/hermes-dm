import argparse
import asyncio
import logging
import sys

# Import the daemon we built
from hermes_dm.daemon.server import PowerSupplyDaemon


def main():
    """Entry point for the hermes-daemon command line interface."""
    parser = argparse.ArgumentParser(description="Hermes Device Manager: Continuous logging and control daemon.")

    parser.add_argument("--db-dir", type=str, default="./logs", help="Directory to store the SQLite database files. (Default: ./logs)")
    parser.add_argument("--cmd-port", type=int, default=5555, help="ZeroMQ REP port for receiving commands. (Default: 5555)")
    parser.add_argument("--pub-port", type=int, default=5556, help="ZeroMQ PUB port for streaming live data. (Default: 5556)")

    args = parser.parse_args()

    # Configure basic console logging
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")

    print("=========================================")
    print(" Hermes Daemon Starting...")
    print(f" Database Directory : {args.db_dir}")
    print(f" Command Port (REP) : {args.cmd_port}")
    print(f" Publish Port (PUB) : {args.pub_port}")
    print("=========================================")

    # Instantiate the daemon with arguments passed from the terminal
    daemon = PowerSupplyDaemon(db_directory=args.db_dir, cmd_port=args.cmd_port, pub_port=args.pub_port)

    # Run the event loop safely
    try:
        asyncio.run(daemon.start())
    except KeyboardInterrupt:
        print("\nShutting down Hermes daemon safely...")
        sys.exit(0)


if __name__ == "__main__":
    main()
