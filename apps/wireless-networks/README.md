# Wireless Networks

## Overview

A comprehensive wireless network management application that provides an intuitive interface for discovering, connecting to, and managing WiFi networks. Features real-time network scanning, connection management, and detailed network information display.

## Features

- **Real-time Network Discovery**: Automatic scanning and listing of available WiFi networks
- **Signal Strength Indicators**: Visual signal strength display with appropriate icons
- **Security Status Display**: Clear indication of network security types and requirements
- **Connection Management**: Easy connect/disconnect operations with password handling
- **Network Information**: Detailed network metadata including BSSID, channel, and data rates
- **Context Menu Actions**: Rich right-click context menu for network operations
- **Search and Filtering**: Filter networks by SSID, BSSID, or security type
- **Auto-refresh**: Automatic network list updates every 10 seconds
- **Toast Notifications**: Connection status feedback with toast messages
- **Password Management**: Secure password entry and credential storage

## Usage

### Basic Operations

#### Connecting to Networks

##### Open Networks
1. **Select Network**: Click on an open network in the list
2. **Auto-connect**: Automatically connects without password prompt
3. **Status Update**: Connection status shown via toast notification

##### Secured Networks
1. **Select Network**: Click on a secured network
2. **Password Dialog**: Enter network password in the dialog
3. **Connect**: Click connect to establish connection
4. **Save Credentials**: Password saved for future automatic connections

##### Previously Connected Networks
1. **Auto-connect**: Click to reconnect using saved credentials
2. **Status Display**: Shows current connection status
3. **Quick Access**: Immediate connection to known networks

#### Network Management
1. **Context Menu**: Right-click networks for additional options
2. **Forget Networks**: Remove saved network credentials
3. **Network Details**: View comprehensive network information
4. **Copy Information**: Copy SSIDs and BSSIDs to clipboard

### Keyboard Shortcuts

#### Navigation
- **Type**: Start filtering networks by typing
- **↑/↓**: Navigate through network list
- **Enter**: Connect to selected network
- **Escape**: Clear search or close application

#### Context Actions
- **Ctrl+J**: Show context menu for selected network
- **Ctrl+Shift+J**: Show global context menu for WiFi management
- **F5**: Force refresh network list
- **Space**: Toggle network selection

#### Global Actions
- **Ctrl+R**: Refresh network scan
- **Ctrl+W**: Toggle WiFi radio on/off
- **Ctrl+I**: Show network interface information

### Context Menu Actions

#### Network-specific Actions
- **Connect/Disconnect**: Toggle connection state for selected network
- **Show Details**: Display comprehensive network information
- **Copy SSID**: Copy network name to clipboard
- **Copy BSSID**: Copy network hardware address to clipboard
- **Forget Network**: Remove saved network credentials
- **View Properties**: Detailed network properties dialog

#### Global WiFi Actions (Ctrl+Shift+J)
- **Refresh Networks**: Force immediate network scan
- **Enable/Disable WiFi**: Toggle WiFi radio state
- **Show Interface Info**: Display WiFi adapter information
- **Connection History**: View recent connection history
- **Network Preferences**: Access network configuration settings

## Features in Detail

### Network Discovery

#### Scanning Process
- **Active Scanning**: Actively probes for available networks
- **Background Updates**: Continuous background scanning
- **Signal Monitoring**: Real-time signal strength updates
- **Network Caching**: Caches network information for performance
- **Duplicate Filtering**: Removes duplicate network entries

#### Network Information
- **SSID**: Network name and identifier
- **BSSID**: Hardware address of access point
- **Signal Strength**: Signal quality and strength indicators
- **Security Type**: WPA, WPA2, WEP, Open network types
- **Channel**: WiFi channel and frequency information
- **Mode**: Infrastructure, Ad-hoc, and other modes
- **Data Rate**: Maximum supported data transmission rate

### Connection Management

#### Connection Process
```bash
# Commands used internally by the application
nmcli device wifi list                    # Scan for networks
nmcli device wifi connect "SSID" password "PASSWORD"  # Connect
nmcli connection up "SSID"               # Reconnect saved
nmcli connection delete "SSID"           # Forget network
```

#### Security Handling
- **WPA/WPA2**: Secure password-based connections
- **WEP**: Legacy WEP encryption support
- **Open Networks**: Unencrypted network connections
- **Enterprise**: Basic enterprise network support
- **Hidden Networks**: Manual connection to hidden SSIDs

#### Credential Management
- **NetworkManager Storage**: Uses system credential storage
- **Automatic Reconnection**: Remembers and reconnects to known networks
- **Password Validation**: Validates passwords before connection attempts
- **Secure Storage**: Passwords stored securely by NetworkManager

### User Interface

#### Visual Elements
- **Signal Icons**: Clear signal strength visualization
- **Security Badges**: Visual security type indicators
- **Connection Status**: Current connection state display
- **Loading Indicators**: Progress indicators during operations
- **Error States**: Clear error messaging and recovery options

#### List Display
- **Network Names**: Primary SSID display
- **Signal Bars**: Graphical signal strength indicators
- **Security Icons**: Lock icons for secured networks
- **Connection Indicators**: Active connection highlighting
- **Sorting**: Networks sorted by signal strength and status

### Search and Filtering

#### Search Capabilities
- **SSID Search**: Filter by network name
- **BSSID Search**: Filter by hardware address
- **Security Filter**: Filter by security type
- **Signal Filter**: Filter by signal strength threshold
- **Connection Filter**: Filter by connection status

#### Advanced Filtering
- **Multiple Criteria**: Combine multiple filter types
- **Real-time Updates**: Filter results update as you type
- **Case Insensitive**: Ignores case in search terms
- **Partial Matching**: Finds partial matches anywhere in fields

## Technical Details

### Architecture

- **Frontend**: GTK4 with Adwaita design system
- **Backend**: NetworkManager integration via nmcli
- **Threading**: Background network operations
- **Caching**: Efficient network information caching
- **Error Handling**: Comprehensive error management

### NetworkManager Integration

#### Command Interface
The application uses NetworkManager's command-line interface:

```python
# Network scanning
subprocess.run(["nmcli", "device", "wifi", "list"])

# Connection management
subprocess.run(["nmcli", "device", "wifi", "connect", ssid, "password", password])

# Interface control
subprocess.run(["nmcli", "radio", "wifi", "on/off"])
```

#### Connection States
- **Connected**: Currently connected to network
- **Connecting**: Connection in progress
- **Disconnected**: Not connected
- **Failed**: Connection attempt failed
- **Available**: Network available for connection

### Performance Optimization

#### Efficient Scanning
- **Adaptive Refresh**: Adjusts scan frequency based on activity
- **Background Processing**: Non-blocking network operations
- **Result Caching**: Caches scan results for immediate display
- **Incremental Updates**: Only updates changed network information

#### Memory Management
- **Object Pooling**: Reuses network list objects
- **Garbage Collection**: Proper cleanup of network objects
- **Resource Monitoring**: Monitors memory usage patterns
- **Efficient Storage**: Compact network information storage

## Configuration

### NetworkManager Configuration

#### WiFi Settings
```bash
# View current WiFi status
nmcli radio wifi

# Check device status
nmcli device status

# View connection profiles
nmcli connection show
```

#### Connection Profiles
```bash
# List saved connections
nmcli connection show

# View specific connection details
nmcli connection show "SSID"

# Delete saved connection
nmcli connection delete "SSID"
```

### Application Settings

#### Refresh Behavior
```python
# Configurable refresh interval (default: 10 seconds)
REFRESH_INTERVAL = 10

# Auto-refresh toggle
AUTO_REFRESH_ENABLED = True
```

#### UI Preferences
```python
# Signal strength display format
SIGNAL_DISPLAY_MODE = "bars"  # or "percentage"

# Sort order preference
SORT_BY_SIGNAL = True
SORT_BY_NAME = False
```

## Use Cases

### Home and Office

- **Quick Connection**: Connect to known networks rapidly
- **Guest Networks**: Easy connection to guest WiFi networks
- **Network Switching**: Switch between home, office, and mobile hotspots
- **Signal Monitoring**: Monitor connection quality and signal strength

### Travel and Mobile

- **Hotel WiFi**: Connect to hotel and public WiFi networks
- **Coffee Shops**: Quick connection to cafe and restaurant WiFi
- **Airport Networks**: Connect to airport and transportation WiFi
- **Mobile Hotspots**: Connect to personal and shared mobile hotspots

### Technical Use

- **Network Troubleshooting**: Diagnose WiFi connectivity issues
- **Site Surveys**: Analyze available networks and signal strength
- **Security Assessment**: Review network security configurations
- **Performance Testing**: Monitor network performance and quality


### Manual Commands
```bash
# Background scanning
nmcli device wifi list --rescan yes

# Quick connection
nmcli device wifi connect "SSID" password "PASSWORD"
```

## Troubleshooting

### Common Issues

1. **No Networks Found**: Check WiFi adapter status and drivers
2. **Connection Failures**: Verify password and network availability
3. **Slow Scanning**: Check NetworkManager service status
4. **Permission Errors**: Ensure user has NetworkManager permissions

### NetworkManager Issues

#### Service Status
```bash
# Check NetworkManager status
systemctl status NetworkManager

# Restart NetworkManager
sudo systemctl restart NetworkManager

# Check for conflicts
sudo systemctl status wpa_supplicant
```

#### Permission Problems
```bash
# Check user groups
groups $USER

# Add user to netdev group (if needed)
sudo usermod -a -G netdev $USER
```

### WiFi Hardware Issues

#### Driver Problems
```bash
# Check WiFi hardware
lspci | grep -i wireless
lsusb | grep -i wireless

# Check driver status
dmesg | grep -i wifi
sudo modprobe -r wifi_driver && sudo modprobe wifi_driver
```

#### Interface Issues
```bash
# Check interface status
ip link show

# Bring interface up
sudo ip link set wlan0 up

# Check for conflicts
sudo rfkill list
```

## Performance Tips

### Optimization Strategies

- **Reduce Scan Frequency**: Increase refresh interval for battery savings
- **Clear Connection History**: Remove unused saved connections
- **Monitor Signal Quality**: Position for optimal signal strength
- **Update Drivers**: Keep WiFi drivers updated for best performance

### Battery Optimization

- **Disable Auto-refresh**: Turn off automatic scanning when on battery
- **Reduce Update Frequency**: Increase refresh intervals for power saving
- **Close When Idle**: Close application when not actively managing networks
- **Monitor Background Activity**: Minimize background network scanning

## Limitations

- Requires NetworkManager for network operations
- Limited to WiFi networks (no Ethernet management)
- Depends on system permissions for network control
- No advanced enterprise network configuration
- Limited to networks supported by NetworkManager
- No built-in VPN integration or management

## Future Enhancements

### Planned Features
- **Network Profiles**: Create and manage network connection profiles
- **VPN Integration**: Built-in VPN connection management
- **Ethernet Support**: Extend to wired network management
- **Enterprise Networks**: Enhanced enterprise network support
- **Network Analytics**: Connection history and performance analytics
- **Advanced Security**: Enhanced security features and monitoring
- **Mobile Hotspot**: Create and manage WiFi hotspots

## Network Information Displayed

- **SSID**: Network name
- **BSSID**: MAC address of the access point
- **Security**: Encryption type (Open, WPA-PSK, WPA2-PSK, etc.)
- **Signal Strength**: Percentage and visual indicator
- **Channel**: Wireless channel number
- **Mode**: Operating mode (Infrastructure, Ad-Hoc)
- **Data Rate**: Maximum supported data rate
- **Connection Status**: Connected, Available, or Connecting

The application provides a comprehensive and user-friendly interface for managing WiFi connections on Linux systems.
