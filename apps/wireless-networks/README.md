# Wireless Networks

A modern GTK4/Libadwaita wireless network manager application that provides an intuitive interface for managing WiFi connections.

## Features

- **Network Discovery**: Automatically scans and lists available WiFi networks
- **Signal Strength**: Visual indicators showing signal strength with appropriate icons
- **Security Status**: Shows network security type (Open, WPA, WPA2, etc.)
- **Connection Management**: Easy connect/disconnect with password prompts
- **Network Information**: Detailed network information including BSSID, channel, mode, and data rate
- **Context Menu**: Right-click context menu for advanced actions
- **Search**: Filter networks by SSID, BSSID, or security type
- **Real-time Updates**: Automatic refresh of network list and connection status

## Usage

### Connecting to Networks
- **Open Networks**: Single click to connect
- **Secured Networks**: Click to connect, enter password in the dialog
- **Connected Networks**: Click to view details

### Context Menu Actions
- **Connect/Disconnect**: Toggle connection status
- **Show Details**: View comprehensive network information
- **Copy SSID/BSSID**: Copy network identifiers to clipboard
- **Forget Network**: Remove saved network credentials

### Global Actions (Ctrl+Shift+J)
- **Refresh Networks**: Force rescan of available networks
- **Enable/Disable WiFi**: Toggle WiFi radio

### Keyboard Shortcuts
- **Ctrl+J**: Show context menu for selected network
- **Ctrl+Shift+J**: Show global context menu
- **Enter**: Connect to selected network
- **Escape**: Clear search or close application
- **Up/Down**: Navigate network list

## Dependencies

The application uses NetworkManager CLI (`nmcli`) for all WiFi operations, ensuring compatibility with most Linux distributions that use NetworkManager.

## Technical Details

- Built with GTK4 and Libadwaita for modern GNOME integration
- Uses the PickerWindow framework for consistent UI patterns
- Threaded network operations to prevent UI blocking
- Automatic refresh every 10 seconds
- Toast notifications for connection status

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
