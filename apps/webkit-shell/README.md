# WebKit Shell

## Overview

A lightweight, customizable web browser shell built on WebKit. Perfect for creating dedicated web application windows, kiosks, or specialized browsing environments with minimal overhead.

## Features

- **WebKit Engine**: Modern web rendering with full HTML5 support
- **Customizable Interface**: Configurable window size, title, and behavior
- **Session Persistence**: Maintains cookies and session data between launches
- **External Link Handling**: Opens external links in the default system browser
- **Command Line Interface**: Launch with specific URLs and configurations
- **Lightweight Design**: Minimal resource footprint
- **Application Integration**: Can be used as a container for web applications
- **Security Features**: Isolated session storage per application ID

## Usage

### Command Line Options

#### Basic Usage
```bash
# Launch with default settings
python webkit-shell.py

# Open specific URL
python webkit-shell.py --url https://example.com

# Custom window size
python webkit-shell.py --width 1200 --height 800

# Custom title
python webkit-shell.py --title "My Web App"
```

#### Advanced Options
```bash
# Custom application ID for separate session storage
python webkit-shell.py --app-id com.example.myapp --url https://app.example.com

# Combine multiple options
python webkit-shell.py \
  --url https://gmail.com \
  --title "Gmail" \
  --width 1024 \
  --height 768 \
  --app-id com.google.gmail
```

### Command Line Arguments

- **--url**: Initial URL to load
- **--width**: Window width in pixels (default: 800)
- **--height**: Window height in pixels (default: 600)
- **--title**: Window title (default: "WebKit Shell")
- **--app-id**: Custom application ID for session isolation

### Navigation

#### Built-in Features
- **Standard Web Navigation**: Back, forward, refresh
- **URL Bar**: Direct URL entry (if enabled)
- **Keyboard Shortcuts**: Standard browser shortcuts
- **Mouse Navigation**: Click, scroll, context menus
- **Touch Support**: Touch gestures on compatible devices

#### External Link Behavior
- **Internal Navigation**: Links within the same domain load normally
- **External Links**: Open in the default system browser
- **New Window Links**: Handled according to configuration
- **Download Links**: Managed by WebKit's download handling

## Features in Detail

### Session Management

#### Data Persistence
- **Cookies**: Persistent cookie storage
- **Local Storage**: Web application local storage
- **Session Storage**: Temporary session data
- **Cache**: Web content caching for performance
- **Credentials**: Saved login credentials (if enabled)

#### Storage Location
Session data is stored in:
```bash
~/.local/share/[APP_ID]/
├── cookies.sqlite
├── cache/
├── local-storage/
└── session-storage/
```

#### Application Isolation
Each unique `app-id` gets separate storage:
- **Isolated Sessions**: Different apps don't share data
- **Security**: Prevents cross-application data leakage
- **Flexibility**: Run multiple web apps independently

### WebKit Configuration

#### Security Features
- **Content Security Policy**: Enforces web security policies
- **JavaScript Sandbox**: Isolated JavaScript execution
- **Cookie Security**: Secure cookie handling
- **HTTPS Enforcement**: Proper SSL/TLS certificate validation

#### Performance Optimization
- **Hardware Acceleration**: GPU-accelerated rendering when available
- **Memory Management**: Efficient memory usage
- **Caching Strategy**: Intelligent content caching
- **Resource Loading**: Optimized resource loading

### Navigation Policy

#### Link Handling Rules
```python
# Internal navigation (same domain)
same_domain_link → Navigate within shell

# External navigation (different domain)
external_link → Open in default browser

# Special protocols
mailto: → Open in email client
tel: → Open in phone app
file: → Handle according to system settings
```

#### Policy Customization
The navigation policy can be customized by modifying the decision handler:
- **Domain Whitelist**: Allow specific external domains
- **Protocol Handling**: Custom handling for special protocols
- **Security Rules**: Enforce security policies
- **User Preferences**: Respect user navigation preferences

## Technical Details

### Architecture

- **Frontend**: GTK4 application framework
- **Rendering**: WebKit2GTK web engine
- **Session Management**: WebKit session and data management
- **Platform Integration**: Native desktop integration

### Dependencies

- `gi` (PyGObject) for GTK interface
- `WebKit2` for web rendering
- `GLib` for system integration
- `Gio` for application framework

### WebKit Features

#### Web Standards Support
- **HTML5**: Full HTML5 specification support
- **CSS3**: Modern CSS features and animations
- **JavaScript**: ES6+ JavaScript support
- **WebAPI**: Modern web APIs (Canvas, WebGL, etc.)
- **Media**: Audio and video playback
- **Fonts**: Web font rendering and support

#### Developer Tools
- **Web Inspector**: Built-in developer tools (if enabled)
- **Console Access**: JavaScript console for debugging
- **Network Monitoring**: Network request inspection
- **Performance Profiling**: Web performance analysis

## Use Cases

### Web Application Containers

#### Dedicated App Windows
```bash
# Gmail client
webkit-shell --app-id com.google.gmail \
             --url https://gmail.com \
             --title "Gmail" \
             --width 1200 --height 800

# Slack workspace
webkit-shell --app-id com.slack.workspace \
             --url https://workspace.slack.com \
             --title "Slack"
```

#### Development Tools
```bash
# Local development server
webkit-shell --url http://localhost:3000 \
             --title "Development Server"

# API documentation
webkit-shell --url http://localhost:8080/docs \
             --title "API Docs"
```

### Kiosk and Display Applications

#### Information Displays
```bash
# Dashboard display
webkit-shell --url https://dashboard.company.com \
             --title "Company Dashboard" \
             --width 1920 --height 1080

# Digital signage
webkit-shell --url https://signage.example.com \
             --app-id com.company.signage \
             --title "Digital Display"
```

#### Public Access
```bash
# Public terminal
webkit-shell --url https://catalog.library.com \
             --title "Library Catalog" \
             --app-id org.library.catalog
```

### Specialized Browsing

#### Isolated Environments
- **Testing**: Test web applications in isolation
- **Security**: Browse untrusted content safely
- **Privacy**: Separate sessions for different purposes
- **Development**: Multiple development environments

## Configuration

### Environment Variables

- **WEBKIT_DISABLE_COMPOSITING**: Disable GPU compositing
- **WEBKIT_FORCE_COMPLEX_TEXT**: Force complex text rendering
- **GTK_DEBUG**: Enable GTK debugging features

### Runtime Configuration

#### WebKit Settings
The shell can be configured to modify WebKit behavior:
- **JavaScript**: Enable/disable JavaScript execution
- **Plugins**: Plugin support configuration
- **Security**: Security policy settings
- **Performance**: Performance optimization settings

#### Application Behavior
- **Window Management**: Window behavior and appearance
- **Navigation**: Navigation policy customization
- **Integration**: Desktop integration features
- **Persistence**: Data persistence settings

## Integration Examples

### Desktop Integration

#### .desktop File
```ini
[Desktop Entry]
Name=My Web App
Exec=webkit-shell --app-id com.example.myapp --url https://app.example.com --title "My App"
Icon=web-browser
Type=Application
Categories=Network;WebBrowser;
```

#### Application Launcher
```bash
#!/bin/bash
# Launch script for web application
exec webkit-shell \
  --app-id com.company.portal \
  --url https://portal.company.com \
  --title "Company Portal" \
  --width 1024 \
  --height 768
```

### Automation and Scripting

#### Batch Operations
```bash
# Launch multiple web apps
webkit-shell --app-id gmail --url https://gmail.com --title "Gmail" &
webkit-shell --app-id calendar --url https://calendar.google.com --title "Calendar" &
webkit-shell --app-id drive --url https://drive.google.com --title "Drive" &
```

## Troubleshooting

### Common Issues

1. **Web Content Not Loading**: Check internet connection and URL validity
2. **Session Data Issues**: Verify write permissions for data directory
3. **External Links**: Ensure default browser is properly configured
4. **Performance Issues**: Check available memory and GPU acceleration

### Debug Mode

Enable debugging for troubleshooting:
```bash
# GTK debugging
GTK_DEBUG=interactive webkit-shell --url https://example.com

# WebKit debugging
WEBKIT_DEBUG=all webkit-shell --url https://example.com
```

### Performance Optimization

- **Memory Usage**: Monitor memory consumption for long-running instances
- **GPU Acceleration**: Ensure proper graphics drivers for hardware acceleration
- **Cache Management**: Periodic cache cleanup for storage management
- **Resource Limits**: Set appropriate resource limits for kiosk environments

## Limitations

- Limited browser UI compared to full-featured browsers
- External link handling depends on system browser configuration
- No built-in bookmark or history management
- WebKit version depends on system WebKit installation
- Plugin support limited to WebKit-supported plugins
- No built-in print functionality (depends on WebKit print support)
