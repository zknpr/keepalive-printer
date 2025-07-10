import win32serviceutil
import win32service
import win32event
import servicemanager
import socket
import time
import logging
from datetime import datetime
import sys
import os
from typing import List


def discover_printer_ports(ip: str, timeout: int = 2) -> List[int]:
    """Discover open ports on the printer"""
    common_printer_ports = [9100, 631, 515, 721, 9101, 9102, 9103, 23, 80, 443]
    open_ports = []

    for port in common_printer_ports:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            result = sock.connect_ex((ip, port))
            if result == 0:
                open_ports.append(port)
            sock.close()
        except:
            pass

    return open_ports


class PrinterKeepAliveService(win32serviceutil.ServiceFramework):
    _svc_name_ = "ToshibaPrinterKeepAlive"
    _svc_display_name_ = "Toshiba Printer Keep-Alive Service"
    _svc_description_ = (
        "Keeps Toshiba B-EX6T printer awake by sending periodic keep-alive commands"
    )

    def __init__(self, args):
        win32serviceutil.ServiceFramework.__init__(self, args)
        self.hWaitStop = win32event.CreateEvent(None, 0, 0, None)
        self.is_running = True

        # Configuration - can be read from config file or registry
        self.printer_ip = "192.168.1.27"  # Updated printer IP
        self.printer_port = 9100
        self.interval = 30  # seconds
        self.keepalive_command = b"\x1b@\x1bA\x1bZ"
        self.max_failures = 10
        self.consecutive_failures = 0

        # Setup logging
        log_path = os.path.join(
            os.path.dirname(__file__), "printer_keepalive_service.log"
        )
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s - %(levelname)s - %(message)s",
            handlers=[logging.FileHandler(log_path), logging.StreamHandler()],
        )
        self.logger = logging.getLogger(__name__)

    def SvcStop(self):
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        self.is_running = False
        win32event.SetEvent(self.hWaitStop)
        self.logger.info("Service stop requested")

    def SvcDoRun(self):
        servicemanager.LogMsg(
            servicemanager.EVENTLOG_INFORMATION_TYPE,
            servicemanager.PYS_SERVICE_STARTED,
            (self._svc_name_, ""),
        )

        self.logger.info("Starting Toshiba Printer Keep-Alive Service")
        self.main()

    def send_keepalive(self):
        """Send keep-alive command to printer"""
        try:
            with socket.create_connection(
                (self.printer_ip, self.printer_port), timeout=5
            ) as sock:
                sock.sendall(self.keepalive_command)
                self.consecutive_failures = 0
                return True
        except Exception as e:
            self.consecutive_failures += 1
            self.logger.error(f"Keep-alive failed (attempt {self.consecutive_failures}): {e}")
            return False

    def test_connection(self):
        """Test if printer is reachable"""
        try:
            with socket.create_connection(
                (self.printer_ip, self.printer_port), timeout=5
            ) as sock:
                return True
        except Exception as e:
            self.logger.error(f"Connection test failed: {e}")
            return False

    def main(self):
        """Main service loop"""
        self.logger.info(
            f"Keep-alive service started for {self.printer_ip}:{self.printer_port}"
        )

        # Initial connection test
        if not self.test_connection():
            self.logger.error("Initial connection test failed. Service will retry...")

        while self.is_running:
            # Check if stop event is set (non-blocking)
            if (
                win32event.WaitForSingleObject(self.hWaitStop, 0)
                == win32event.WAIT_OBJECT_0
            ):
                break

            try:
                if self.send_keepalive():
                    self.logger.debug("Keep-alive sent successfully")
                else:
                    self.logger.warning(f"Keep-alive failed ({self.consecutive_failures} consecutive failures)")
                    
                    if self.consecutive_failures >= self.max_failures:
                        self.logger.error(f"Max failures ({self.max_failures}) reached. Will keep trying...")
                        # Don't break, keep trying - this is a service that should be resilient

                # Wait for interval or stop event
                if (
                    win32event.WaitForSingleObject(self.hWaitStop, self.interval * 1000)
                    == win32event.WAIT_OBJECT_0
                ):
                    break

            except Exception as e:
                self.logger.error(f"Unexpected error: {e}")
                time.sleep(5)

        self.logger.info("Keep-alive service stopped")


if __name__ == "__main__":
    if len(sys.argv) == 1:
        servicemanager.Initialize()
        servicemanager.PrepareToHostSingle(PrinterKeepAliveService)
        servicemanager.StartServiceCtrlDispatcher()
    else:
        win32serviceutil.HandleCommandLine(PrinterKeepAliveService)

# Installation commands:
# python winservice.py install
# python winservice.py start
# python winservice.py stop
# python winservice.py remove
#
# To check status:
# python winservice.py status
#
# To run interactively for testing:
# python winservice.py debug
