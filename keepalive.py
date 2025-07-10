import socket
import time
import logging
import sys
from datetime import datetime
import threading
from typing import Optional, List


def discover_printer_ports(ip: str, timeout: int = 2) -> List[int]:
    """Discover open ports on the printer that might accept print jobs"""
    common_printer_ports = [9100, 631, 515, 721, 9101, 9102, 9103, 23, 80, 443]
    open_ports = []

    print(f"Scanning {ip} for open printer ports...")
    for port in common_printer_ports:
        try:
            with socket.create_connection((ip, port), timeout=timeout) as sock:
                open_ports.append(port)
                print(f"  Port {port}: OPEN")
        except (socket.timeout, socket.error):
            print(f"  Port {port}: CLOSED")

    return open_ports


def test_printer_communication(ip: str, port: int) -> bool:
    """Test if we can communicate with the printer on a specific port"""
    test_commands = [
        b"\x1b@\x1bA\x1bZ",  # SBPL keep-alive
        b"\x1b@",            # ESC @ (Initialize printer)
        b"\r\n",             # Simple carriage return
    ]

    print(f"Testing communication with {ip}:{port}...")
    for i, cmd in enumerate(test_commands):
        try:
            with socket.create_connection((ip, port), timeout=3) as sock:
                sock.sendall(cmd)
                sock.settimeout(1)
                try:
                    response = sock.recv(1024)
                    print(
                        f"  Command {i+1}: SUCCESS (got response: {response[:20]}...)"
                    )
                    return True
                except socket.timeout:
                    print(f"  Command {i+1}: SENT (no response expected)")
                    return True
        except Exception as e:
            print(f"  Command {i+1}: FAILED ({e})")

    return False


class PrinterKeepAlive:
    def __init__(self, printer_ip: str, printer_port: int = 9100, interval: int = 30):
        self.printer_ip = printer_ip
        self.printer_port = printer_port
        self.interval = interval
        self.keepalive_command = b"\x1b@\x1bA\x1bZ"  # SBPL keep-alive
        self.running = False
        self.last_success = None
        self.consecutive_failures = 0
        self.max_failures = 10

        # Setup logging
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s - %(levelname)s - %(message)s",
            handlers=[
                logging.FileHandler("printer_keepalive.log"),
                logging.StreamHandler(sys.stdout),
            ],
        )
        self.logger = logging.getLogger(__name__)

    def test_connection(self) -> bool:
        """Test if printer is reachable"""
        try:
            with socket.create_connection(
                (self.printer_ip, self.printer_port), timeout=5
            ) as sock:
                return True
        except Exception as e:
            self.logger.error(f"Connection test failed: {e}")
            return False

    def send_keepalive(self) -> bool:
        """Send keep-alive command to printer"""
        try:
            with socket.create_connection(
                (self.printer_ip, self.printer_port), timeout=5
            ) as sock:
                sock.sendall(self.keepalive_command)
                sock.settimeout(2)  # Wait for any response/acknowledgment
                try:
                    # Try to read any response (some printers send ACK)
                    response = sock.recv(1024)
                except socket.timeout:
                    pass  # No response expected for keep-alive

                self.last_success = datetime.now()
                self.consecutive_failures = 0
                return True

        except Exception as e:
            self.consecutive_failures += 1
            self.logger.warning(
                f"Keep-alive failed (attempt {self.consecutive_failures}): {e}"
            )
            return False

    def get_status(self) -> dict:
        """Get current status of the keep-alive service"""
        return {
            "running": self.running,
            "printer_ip": self.printer_ip,
            "last_success": (
                self.last_success.isoformat() if self.last_success else None
            ),
            "consecutive_failures": self.consecutive_failures,
            "uptime": (
                str(datetime.now() - self.start_time)
                if hasattr(self, "start_time")
                else None
            ),
        }

    def run(self):
        """Main keep-alive loop"""
        self.running = True
        self.start_time = datetime.now()
        self.logger.info(
            f"Starting keep-alive service for printer {self.printer_ip}:{self.printer_port}"
        )

        # Initial connection test
        if not self.test_connection():
            self.logger.error("Initial connection test failed. Exiting.")
            return

        while self.running:
            try:
                if self.send_keepalive():
                    self.logger.debug("Keep-alive sent successfully")
                else:
                    if self.consecutive_failures >= self.max_failures:
                        self.logger.error(
                            f"Max failures ({self.max_failures}) reached. Stopping service."
                        )
                        break

                time.sleep(self.interval)

            except KeyboardInterrupt:
                self.logger.info("Received interrupt signal. Stopping...")
                break
            except Exception as e:
                self.logger.error(f"Unexpected error: {e}")
                time.sleep(5)  # Wait before retry

        self.running = False
        self.logger.info("Keep-alive service stopped")

    def stop(self):
        """Stop the keep-alive service"""
        self.running = False


# Configuration
PRINTER_IP = "192.168.1.27"  # Updated printer IP
PRINTER_PORT = 9100
KEEPALIVE_INTERVAL = 30  # seconds

if __name__ == "__main__":
    # First, discover available ports on the printer
    print(f"Discovering printer ports on {PRINTER_IP}...")
    open_ports = discover_printer_ports(PRINTER_IP)
    
    if not open_ports:
        print(f"No open ports found on {PRINTER_IP}. Please check:")
        print("1. The IP address is correct")
        print("2. The printer is powered on and connected to the network")
        print("3. Your computer can reach the printer (try ping)")
        sys.exit(1)
    
    print(f"\nFound {len(open_ports)} open port(s): {open_ports}")
    
    # Test communication on each port
    working_port = None
    for port in open_ports:
        if test_printer_communication(PRINTER_IP, port):
            working_port = port
            print(f"\n✓ Port {port} appears to work for printer communication!")
            break
    
    if working_port:
        # Ask user if they want to use the discovered port
        response = input(f"\nUse port {working_port}? (y/n, default: y): ").strip().lower()
        if response in ('', 'y', 'yes'):
            PRINTER_PORT = working_port
        else:
            port_input = input(f"Enter port to use (default: {PRINTER_PORT}): ").strip()
            if port_input.isdigit():
                PRINTER_PORT = int(port_input)
    else:
        print(f"\n⚠ No ports responded to printer commands. Using default port {PRINTER_PORT}")
        print("The service will still attempt to connect, but may not work properly.")
    
    print(f"\nStarting keep-alive service for {PRINTER_IP}:{PRINTER_PORT}")
    service = PrinterKeepAlive(PRINTER_IP, PRINTER_PORT, KEEPALIVE_INTERVAL)

    try:
        service.run()
    except Exception as e:
        print(f"Service failed: {e}")
        sys.exit(1)
