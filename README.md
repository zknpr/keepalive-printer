# Toshiba Printer Keep-Alive Service

A multi-platform solution to keep Toshiba B-EX6T printers (and other network printers) awake by sending periodic keep-alive commands. This prevents the printer from going into sleep mode and becoming unresponsive.

## 🖨️ Problem Statement

Some network printers, particularly Toshiba B-EX6T models, enter a deep sleep mode after periods of inactivity. When in this state, they may:
- Stop responding to network ping requests
- Refuse print job connections
- Require manual wake-up (power cycle or physical interaction)

This service solves the problem by sending periodic SBPL (Standard Business Programming Language) keep-alive commands to maintain the printer's active state.

## 📁 Project Structure

```
keepalive-printer/
├── keepalive.py              # Cross-platform Python script with port discovery
├── winservice.py             # Windows service implementation
├── ToshibaKeepAlive.psm1     # PowerShell module for Windows
├── requirements.txt          # Python dependencies
└── README.md                 # This file
```

## 📦 Installation

### Prerequisites

- **Python 3.6+** for Python scripts
- **PowerShell 5.1+** for PowerShell module (Windows only)

### Install Dependencies

1. **Clone or download** this repository
2. **Install Python dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

### Dependency Details

- **`pywin32`** (Windows only): Required **only** for Windows service functionality (`winservice.py`)
- **All other modules**: Built into Python standard library (socket, time, logging, datetime, threading, typing)

**Note**: 
- The main script (`keepalive.py`) works on all platforms without any dependencies
- Only install `pywin32` if you plan to use the Windows service option
- On macOS/Linux, you can skip `pip install -r requirements.txt` entirely

## 🔧 Configuration

All scripts are pre-configured for:
- **Printer IP**: `192.168.1.27`
- **Default Port**: `9100` (Raw/Direct IP printing)
- **Keep-alive Interval**: `30 seconds`
- **Keep-alive Command**: `ESC @ ESC A ESC Z` (SBPL sequence)

## 🚀 Quick Start

### Option 1: Python Script (Recommended - Cross-platform)

1. **Install Python 3.6+** if not already installed
2. **Run the script directly** (no dependencies needed):
   ```bash
   python keepalive.py
   ```
   *Or install dependencies if you plan to use Windows service later:*
   ```bash
   pip install -r requirements.txt
   ```
3. **The script will automatically**:
   - Scan for open ports on your printer
   - Test communication on each port
   - Ask you to confirm the working port
   - Start the keep-alive service

**Example Output**:
```
Discovering printer ports on 192.168.1.27...
Scanning 192.168.1.27 for open printer ports...
  Port 9100: OPEN
  Port 631: CLOSED
  Port 515: CLOSED
  ...

Found 1 open port(s): [9100]

Testing communication with 192.168.1.27:9100...
  Command 1: SUCCESS (no response expected)

✓ Port 9100 appears to work for printer communication!

Use port 9100? (y/n, default: y): y

Starting keep-alive service for 192.168.1.27:9100
2025-07-10 10:30:00 - INFO - Starting keep-alive service for printer 192.168.1.27:9100
```

### Option 2: Windows Service

For production environments where you want the service to start automatically with Windows:

1. **Install dependencies**:
   ```cmd
   pip install -r requirements.txt
   ```
2. **Open Command Prompt as Administrator**
3. **Install the service**:
   ```cmd
   python winservice.py install
   ```
4. **Start the service**:
   ```cmd
   python winservice.py start
   ```

**Service Management**:
```cmd
# Check service status
python winservice.py status

# Stop the service
python winservice.py stop

# Remove the service
python winservice.py remove

# Run interactively for testing
python winservice.py debug
```

### Option 3: PowerShell Module

For Windows environments with PowerShell:

1. **Open PowerShell as Administrator**
2. **Import the module**:
   ```powershell
   Import-Module .\ToshibaKeepAlive.psm1
   ```
3. **Discover printer ports**:
   ```powershell
   Find-PrinterPorts -PrinterIP "192.168.1.27"
   ```
4. **Test communication**:
   ```powershell
   Test-PrinterCommunication -PrinterIP "192.168.1.27" -PrinterPort 9100
   ```
5. **Start keep-alive service**:
   ```powershell
   Start-PrinterKeepAlive
   ```

**Install as Scheduled Task**:
```powershell
Install-KeepAliveTask -PrinterIP "192.168.1.27"
```

## 🔍 Troubleshooting

### Printer Not Found

If no open ports are discovered:

1. **Verify IP address**: Ping the printer
   ```bash
   ping 192.168.1.27
   ```

2. **Check network connectivity**: Ensure your computer and printer are on the same network

3. **Verify printer is powered on**: Check physical status

4. **Try other IP addresses**: Check your router's DHCP client list

### Connection Refused

If ports are open but communication fails:

1. **Check firewall settings**: Both on your computer and printer
2. **Try different ports**: Some printers use non-standard ports
3. **Verify printer supports SBPL**: Consult printer documentation

### Service Stops Working

1. **Check logs**:
   - Python script: `printer_keepalive.log`
   - Windows service: `printer_keepalive_service.log`
   - PowerShell: `C:\ProgramData\ToshibaKeepAlive\keepalive.log`

2. **Common issues**:
   - Printer IP changed (DHCP)
   - Network configuration changed
   - Printer firmware updated

## 📊 Monitoring

### Log Locations

- **Python script**: `./printer_keepalive.log`
- **Windows service**: `./printer_keepalive_service.log`
- **PowerShell module**: `C:\ProgramData\ToshibaKeepAlive\keepalive.log`

### Log Levels

- **INFO**: Service start/stop, successful operations
- **DEBUG**: Individual keep-alive commands
- **WARNING**: Failed keep-alive attempts
- **ERROR**: Critical failures, connection issues

### Sample Log Entry
```
2025-07-10 10:30:15 - INFO - Keep-alive sent successfully
2025-07-10 10:30:45 - WARNING - Keep-alive failed (attempt 1): [Errno 111] Connection refused
2025-07-10 10:31:15 - INFO - Keep-alive sent successfully
```

## 🔧 Advanced Configuration

### Changing Settings

Edit the configuration section in any script:

**Python (`keepalive.py`)**:
```python
PRINTER_IP = "192.168.1.27"
PRINTER_PORT = 9100
KEEPALIVE_INTERVAL = 30  # seconds
```

**Windows Service (`winservice.py`)**:
```python
self.printer_ip = "192.168.1.27"
self.printer_port = 9100
self.interval = 30  # seconds
```

**PowerShell (`ToshibaKeepAlive.psm1`)**:
```powershell
$script:Config = @{
    PrinterIP = "192.168.1.27"
    PrinterPort = 9100
    Interval = 30
}
```

### Supported Printer Ports

The scripts automatically test these common printer ports:

- **9100**: Raw/Direct IP printing (most common)
- **631**: IPP (Internet Printing Protocol)
- **515**: LPR/LPD (Line Printer Remote/Daemon)
- **721**: Often used by network printers
- **9101-9103**: Alternative raw printing ports
- **23**: Telnet (for printer management)
- **80/443**: HTTP/HTTPS (web interface)

## 🔄 Keep-Alive Commands

The service sends these SBPL commands in sequence:

1. **ESC @** (`0x1B 0x40`): Initialize printer
2. **ESC A** (`0x1B 0x41`): Set print mode
3. **ESC Z** (`0x1B 0x5A`): Print status request

This sequence is designed to wake up the printer without actually printing anything.

## 🆘 Support

### Compatibility

- **Tested with**: Toshiba B-EX6T series
- **Should work with**: Most SBPL-compatible printers
- **Platforms**: Windows, macOS, Linux
- **Python**: 3.6+ required
- **PowerShell**: 5.1+ required (Windows only)

### Getting Help

1. **Check logs first**: Most issues are logged with helpful error messages
2. **Verify network connectivity**: Use ping and port scanners
3. **Test manually**: Use telnet to test printer ports
   ```bash
   telnet 192.168.1.27 9100
   ```
4. **Consult printer documentation**: For printer-specific command sequences

### Common Error Messages

| Error | Cause | Solution |
|-------|-------|----------|
| `Connection refused` | Printer not listening on port | Check IP/port, verify printer is on |
| `Host unreachable` | Network issue | Check network connectivity, IP address |
| `Timeout` | Printer slow to respond | Increase timeout in script |
| `Permission denied` | Firewall blocking | Check firewall settings |

## 📝 License

This project is provided as-is for educational and operational purposes. Modify as needed for your environment.

## 🔄 Version History

- **v1.0**: Initial release with basic keep-alive functionality
- **v1.1**: Added port discovery and communication testing
- **v1.2**: Improved error handling and logging
- **v1.3**: Added PowerShell module and Windows service options
