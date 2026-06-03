import argparse
import time
import sys
from hermes_dm.client.connection import HermesClient, HermesError
from hermes_dm.client.telemetry import HermesTelemetryListener

def print_live_data(topic: str, data: dict):
    """Callback function to format and print incoming telemetry."""
    timestamp = data.get("timestamp", "").split("T")[-1] # Just get the time part
    metric = data.get("metric", "Unknown")
    value = data.get("value", "N/A")
    channel = data.get("channel", 1)
    
    print(f"[{timestamp}] {topic} (Ch{channel}) -> {metric}: {value}")

def main():
    parser = argparse.ArgumentParser(
        description="Hermes Monitor: Connect an instrument and stream live data."
    )
    
    # Daemon connection arguments
    parser.add_argument("--host", default="localhost", help="Daemon host IP (default: localhost)")
    parser.add_argument("--cmd-port", type=int, default=5555, help="Daemon command port (default: 5555)")
    parser.add_argument("--pub-port", type=int, default=5556, help="Daemon telemetry port (default: 5556)")
    
    # Instrument arguments
    parser.add_argument("--name", required=True, help="Short name for the device (e.g., Main_PSU)")
    parser.add_argument("--model", required=True, help="Driver model (e.g., Keithley2410)")
    parser.add_argument("--identifier", required=True, help="PyVISA identifier (e.g., USB0::0x1234::INSTR)")
    parser.add_argument("--interval", type=float, default=1.0, help="Polling interval in seconds (default: 1.0)")

    args = parser.parse_args()

    print("=========================================")
    print(f" Hermes Monitor: {args.name}")
    print("=========================================")

    # 1. Setup the Telemetry Listener in the background
    listener = HermesTelemetryListener(host=args.host, port=args.pub_port)
    listener.subscribe(f"DATA.{args.name}") 
    listener.start(callback=print_live_data)

    # 2. Connect the Command Client
    try:
        with HermesClient(host=args.host, port=args.cmd_port) as client:
            
            print(f"Connecting to {args.identifier} as {args.model}...")
            client.connect_device(args.name, args.model, args.identifier)
            
            print(f"Setting polling interval to {args.interval}s...")
            client.set_interval(args.name, args.interval)
            
            # Optional: Enable output if it's a known power supply behavior
            # client.configure_device(args.name, {"output_enabled": True})
            
            print("\nStarting logging. Waiting for telemetry (Press Ctrl+C to stop)...\n")
            client.start_logging()
            
            # Keep the main thread alive while the background listener prints data
            while True:
                time.sleep(0.1)

    except KeyboardInterrupt:
        print("\n\nShutting down monitor gracefully...")
    except HermesError as e:
        print(f"\n[Daemon Error] {e}")
    except Exception as e:
        print(f"\n[Error] {e}")
    finally:
        # 3. Clean up regardless of how we exit
        print("Stopping logging and closing connections...")
        try:
            with HermesClient(host=args.host, port=args.cmd_port) as client:
                client.stop_logging()
        except:
            pass # Daemon might already be dead
            
        listener.stop()
        sys.exit(0)

if __name__ == "__main__":
    main()