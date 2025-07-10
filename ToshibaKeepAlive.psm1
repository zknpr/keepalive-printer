# ToshibaKeepAlive.psm1 - PowerShell Module for Toshiba Printer Keep-Alive

# Configuration
$script:Config = @{
    PrinterIP = "192.168.1.27"
    PrinterPort = 9100
    Interval = 30
    MaxRetries = 10
    LogFile = "C:\ProgramData\ToshibaKeepAlive\keepalive.log"
    TestPorts = @(9100, 631, 515, 721, 9101, 9102, 9103, 23, 80, 443)
}

# Ensure log directory exists
$logDir = Split-Path $script:Config.LogFile
if (-not (Test-Path $logDir)) {
    New-Item -ItemType Directory -Path $logDir -Force | Out-Null
}

function Write-KeepAliveLog {
    param(
        [string]$Message,
        [string]$Level = "INFO"
    )
    
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $logEntry = "$timestamp - $Level - $Message"
    
    # Write to console and log file
    Write-Host $logEntry
    Add-Content -Path $script:Config.LogFile -Value $logEntry
}

function Test-PrinterConnection {
    param(
        [string]$PrinterIP = $script:Config.PrinterIP,
        [int]$PrinterPort = $script:Config.PrinterPort
    )
    
    try {
        $tcpClient = New-Object System.Net.Sockets.TcpClient
        $tcpClient.ReceiveTimeout = 3000
        $tcpClient.SendTimeout = 3000
        
        $tcpClient.Connect($PrinterIP, $PrinterPort)
        $connected = $tcpClient.Connected
        $tcpClient.Close()
        
        return $connected
    }
    catch {
        Write-KeepAliveLog "Connection test failed: $($_.Exception.Message)" "ERROR"
        return $false
    }
}

function Send-KeepAliveCommand {
    param(
        [string]$PrinterIP = $script:Config.PrinterIP,
        [int]$PrinterPort = $script:Config.PrinterPort
    )
    
    try {
        $tcpClient = New-Object System.Net.Sockets.TcpClient
        $tcpClient.ReceiveTimeout = 3000
        $tcpClient.SendTimeout = 3000
        
        $tcpClient.Connect($PrinterIP, $PrinterPort)
        $stream = $tcpClient.GetStream()
        
        # SBPL keep-alive command: ESC @ ESC A ESC Z
        $keepaliveBytes = [byte[]](0x1B, 0x40, 0x1B, 0x41, 0x1B, 0x5A)
        $stream.Write($keepaliveBytes, 0, $keepaliveBytes.Length)
        $stream.Flush()
        
        $stream.Close()
        $tcpClient.Close()
        
        return $true
    }
    catch {
        Write-KeepAliveLog "Keep-alive command failed: $($_.Exception.Message)" "ERROR"
        return $false
    }
}

function Start-PrinterKeepAlive {
    param(
        [string]$PrinterIP = $script:Config.PrinterIP,
        [int]$PrinterPort = $script:Config.PrinterPort,
        [int]$Interval = $script:Config.Interval
    )
    
    Write-KeepAliveLog "Starting keep-alive service for $PrinterIP:$PrinterPort"
    
    # Initial connection test
    if (-not (Test-PrinterConnection -PrinterIP $PrinterIP -PrinterPort $PrinterPort)) {
        Write-KeepAliveLog "Initial connection test failed. Exiting." "ERROR"
        return
    }
    
    $consecutiveFailures = 0
    $maxFailures = $script:Config.MaxRetries
    
    try {
        while ($true) {
            if (Send-KeepAliveCommand -PrinterIP $PrinterIP -PrinterPort $PrinterPort) {
                Write-KeepAliveLog "Keep-alive sent successfully" "DEBUG"
                $consecutiveFailures = 0
            }
            else {
                $consecutiveFailures++
                Write-KeepAliveLog "Keep-alive failed (attempt $consecutiveFailures of $maxFailures)" "WARNING"
                
                if ($consecutiveFailures -ge $maxFailures) {
                    Write-KeepAliveLog "Max failures reached. Stopping service." "ERROR"
                    break
                }
            }
            
            Start-Sleep -Seconds $Interval
        }
    }
    catch {
        Write-KeepAliveLog "Service interrupted: $($_.Exception.Message)" "ERROR"
    }
    
    Write-KeepAliveLog "Keep-alive service stopped"
}

function Install-KeepAliveTask {
    param(
        [string]$TaskName = "ToshibaPrinterKeepAlive",
        [string]$PrinterIP = $script:Config.PrinterIP
    )
    
    $scriptPath = $MyInvocation.ScriptName
    $action = New-ScheduledTaskAction -Execute "PowerShell.exe" -Argument "-ExecutionPolicy Bypass -Command `"Import-Module '$scriptPath'; Start-PrinterKeepAlive -PrinterIP '$PrinterIP'`""
    $trigger = New-ScheduledTaskTrigger -AtStartup
    $settings = New-ScheduledTaskSettingsSet -DontStopIfGoingOnBatteries -DontStopOnIdleEnd -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 1)
    
    Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Settings $settings -User "SYSTEM" -RunLevel Highest
    
    Write-KeepAliveLog "Scheduled task '$TaskName' installed successfully"
}

function Remove-KeepAliveTask {
    param(
        [string]$TaskName = "ToshibaPrinterKeepAlive"
    )
    
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
    Write-KeepAliveLog "Scheduled task '$TaskName' removed"
}

function Find-PrinterPorts {
    param(
        [string]$PrinterIP = $script:Config.PrinterIP,
        [int[]]$Ports = $script:Config.TestPorts,
        [int]$TimeoutMs = 2000
    )
    
    Write-KeepAliveLog "Scanning $PrinterIP for open printer ports..."
    $openPorts = @()
    
    foreach ($port in $Ports) {
        try {
            $tcpClient = New-Object System.Net.Sockets.TcpClient
            $tcpClient.ReceiveTimeout = $TimeoutMs
            $tcpClient.SendTimeout = $TimeoutMs
            
            $result = $tcpClient.BeginConnect($PrinterIP, $port, $null, $null)
            $success = $result.AsyncWaitHandle.WaitOne($TimeoutMs, $false)
            
            if ($success -and $tcpClient.Connected) {
                $openPorts += $port
                Write-KeepAliveLog "  Port $port : OPEN" "INFO"
            } else {
                Write-KeepAliveLog "  Port $port : CLOSED" "DEBUG"
            }
            
            $tcpClient.Close()
        }
        catch {
            Write-KeepAliveLog "  Port $port : ERROR - $($_.Exception.Message)" "DEBUG"
        }
    }
    
    return $openPorts
}

function Test-PrinterCommunication {
    param(
        [string]$PrinterIP = $script:Config.PrinterIP,
        [int]$PrinterPort = $script:Config.PrinterPort
    )
    
    $testCommands = @(
        @{ Name = "SBPL Keep-alive"; Bytes = [byte[]](0x1B, 0x40, 0x1B, 0x41, 0x1B, 0x5A) },
        @{ Name = "ESC @ Initialize"; Bytes = [byte[]](0x1B, 0x40) },
        @{ Name = "Simple CRLF"; Bytes = [System.Text.Encoding]::ASCII.GetBytes("`r`n") }
    )
    
    Write-KeepAliveLog "Testing communication with $PrinterIP`:$PrinterPort..."
    
    foreach ($cmd in $testCommands) {
        try {
            $tcpClient = New-Object System.Net.Sockets.TcpClient
            $tcpClient.ReceiveTimeout = 3000
            $tcpClient.SendTimeout = 3000
            
            $tcpClient.Connect($PrinterIP, $PrinterPort)
            $stream = $tcpClient.GetStream()
            
            $stream.Write($cmd.Bytes, 0, $cmd.Bytes.Length)
            $stream.Flush()
            
            # Try to read response
            $buffer = New-Object byte[] 1024
            $stream.ReadTimeout = 1000
            try {
                $bytesRead = $stream.Read($buffer, 0, $buffer.Length)
                if ($bytesRead -gt 0) {
                    Write-KeepAliveLog "  $($cmd.Name): SUCCESS (got response)" "INFO"
                } else {
                    Write-KeepAliveLog "  $($cmd.Name): SUCCESS (no response)" "INFO"
                }
            }
            catch [System.IO.IOException] {
                Write-KeepAliveLog "  $($cmd.Name): SUCCESS (timeout on read)" "INFO"
            }
            
            $stream.Close()
            $tcpClient.Close()
            return $true
        }
        catch {
            Write-KeepAliveLog "  $($cmd.Name): FAILED - $($_.Exception.Message)" "WARNING"
        }
    }
    
    return $false
}

# Export functions
Export-ModuleMember -Function Test-PrinterConnection, Send-KeepAliveCommand, Start-PrinterKeepAlive, Install-KeepAliveTask, Remove-KeepAliveTask, Find-PrinterPorts, Test-PrinterCommunication, Find-PrinterPorts, Test-PrinterCommunication

# Usage examples:
# Import-Module .\ToshibaKeepAlive.psm1
# Find-PrinterPorts -PrinterIP "192.168.1.27"
# Test-PrinterCommunication -PrinterIP "192.168.1.27" -PrinterPort 9100
# Test-PrinterConnection
# Install-KeepAliveTask -PrinterIP "192.168.1.27"
# Start-PrinterKeepAlive