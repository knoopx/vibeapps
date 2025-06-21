# Windows

## Overview

A comprehensive window management application designed specifically for the Niri compositor. Provides visual window listing, advanced search capabilities, and convenient window control operations with real-time status updates.

## Features

- **Real-time Window List**: Live display of all open windows with automatic updates
- **Advanced Search**: Filter windows by title, app ID, workspace, or process ID
- **Window Focus Control**: Instantly focus any window with click or keyboard
- **Window Management**: Close windows directly from the interface
- **Status Indicators**: Visual badges for focused, urgent, and floating windows
- **Context Menu Actions**: Rich right-click context menu for window operations
- **Clipboard Integration**: Copy window IDs, titles, and other information
- **Auto-refresh**: Automatically updates window list every 5 seconds
- **Application Icons**: Displays appropriate icons for recognized applications
- **Workspace Information**: Shows which workspace each window belongs to

## Usage

### Basic Operations

#### Window Navigation

1. **View Windows**: Launch to see all open windows
2. **Search**: Type to filter windows by various criteria
3. **Focus**: Click or press Enter to focus selected window
4. **Manage**: Use context menu for additional actions

#### Window Control

1. **Focus Window**: Click window or press Enter
2. **Close Window**: Use context menu to close windows
3. **Copy Information**: Copy window details to clipboard
4. **Monitor Status**: View window status with visual indicators

### Keyboard Shortcuts

#### Navigation

- **Type**: Start filtering windows immediately
- **↑/↓**: Navigate through window list
- **Enter**: Focus selected window
- **Escape**: Clear search or close application

#### Actions

- **Ctrl+J**: Show context menu for selected window
- **F5**: Force refresh window list
- **Delete**: Close selected window (via context menu)

#### Quick Access

- **Alt+Tab**: Alternative window switching (system)
- **Space**: Preview window information

### Search Capabilities

#### Search Criteria

- **Window Title**: Filter by window title text
- **Application ID**: Search by app identifier
- **Window ID**: Find specific window by ID
- **Workspace**: Filter by workspace name or number
- **Process ID**: Search by process identifier

#### Search Examples

```
firefox → Firefox browser windows
terminal → Terminal applications
workspace 2 → Windows on workspace 2
code → Code editor windows
1234 → Window or process with ID 1234
```

## Features in Detail

### Niri Integration

#### Window Information Source

The application integrates directly with Niri compositor:

```bash
# Command used internally
niri msg --json windows
```

#### Window Control Commands

```bash
# Focus window (used internally)
niri msg action focus-window --id <window_id>

# Close window (used internally)
niri msg action close-window --id <window_id>
```

#### Real-time Updates

- **Automatic Refresh**: Updates every 5 seconds
- **Manual Refresh**: Force refresh with F5
- **Event-driven**: Responds to window state changes
- **Efficient Polling**: Minimal system impact

### Window Status Indicators

#### Visual Badges

- **Focused Window**: Highlighted indicator for currently focused window
- **Urgent Window**: Special marking for windows requiring attention
- **Floating Window**: Indicator for floating (non-tiled) windows
- **Minimized Window**: Status for minimized windows
- **Fullscreen Window**: Indicator for fullscreen applications

#### Status Information

- **Workspace Location**: Shows which workspace contains the window
- **Application Type**: Identifies application category
- **Window State**: Displays current window state
- **Process Information**: Shows process ID and details

### Context Menu Actions

#### Primary Actions

- **Focus Window**: Bring window to foreground and focus
- **Close Window**: Safely close the selected window
- **Move to Workspace**: Move window to different workspace
- **Toggle Floating**: Switch between tiled and floating mode

#### Information Actions

- **Copy Window ID**: Copy unique window identifier
- **Copy Title**: Copy window title to clipboard
- **Copy App ID**: Copy application identifier
- **Show Details**: Display comprehensive window information

#### Advanced Actions

- **Minimize/Restore**: Toggle window minimization
- **Maximize/Restore**: Toggle window maximization
- **Always on Top**: Pin window above others
- **Send to Background**: Move window to background

### Application Icons

#### Icon Sources

- **Desktop Files**: Icons from .desktop entries
- **System Icons**: Standard system application icons
- **Theme Icons**: Icons from current icon theme
- **Fallback Icons**: Generic icons for unknown applications

#### Icon Display

- **High Resolution**: Crisp icons at multiple sizes
- **Consistent Sizing**: Uniform icon dimensions
- **Adaptive**: Adjusts to interface scaling
- **Placeholder**: Generic icon for unrecognized apps

## Technical Details

### Architecture

- **Frontend**: GTK4 with Adwaita design system
- **Backend**: Direct Niri compositor integration
- **Communication**: JSON-based IPC with Niri
- **Threading**: Background updates with UI responsiveness
- **Caching**: Efficient window information caching

### Niri Integration

#### IPC Protocol

```python
# Get window list
import subprocess
import json

result = subprocess.run(
    ["niri", "msg", "--json", "windows"],
    capture_output=True,
    text=True
)
windows = json.loads(result.stdout)
```

#### Window Data Structure

```json
{
  "id": 12345,
  "title": "Window Title",
  "app_id": "application.id",
  "workspace_id": 1,
  "pid": 6789,
  "is_focused": false,
  "is_urgent": false,
  "is_floating": false
}
```

### Performance Optimization

#### Efficient Updates

- **Incremental Updates**: Only update changed windows
- **Lazy Loading**: Load details on demand
- **Background Processing**: Non-blocking window operations
- **Memory Management**: Efficient memory usage

#### Search Optimization

- **Index Caching**: Cache search indices for fast filtering
- **Pattern Matching**: Efficient string matching algorithms
- **Result Limiting**: Limit displayed results for performance
- **Debounced Search**: Optimize search frequency

## Configuration

### Niri Configuration

#### Window Rules

Configure Niri for optimal integration:

```kdl
// niri.kdl - Example window rules
window-rule {
    match app-id="net.knoopx.windows"
    default-column-width { proportion 0.3; }
    open-on-output "primary"
}
```

#### IPC Settings

```kdl
// Enable IPC for window management
input {
    keyboard {
        xkb {
            layout "us"
            options "grp:alt_shift_toggle"
        }
    }
}
```

### Application Settings

#### Auto-refresh Interval

```python
# Configurable refresh rate (default: 5 seconds)
REFRESH_INTERVAL = 5
```

#### Search Behavior

```python
# Search configuration
SEARCH_DEBOUNCE = 300  # milliseconds
MAX_RESULTS = 100      # maximum displayed results
CASE_SENSITIVE = False # case-sensitive search
```

## Use Cases

### Window Management

- **Multi-workspace Navigation**: Quickly find windows across workspaces
- **Application Switching**: Alternative to Alt+Tab for window switching
- **Window Organization**: Organize and manage multiple open windows
- **Focus Management**: Efficiently focus specific windows

### Productivity

- **Development Workflow**: Manage multiple development tools and editors
- **Research**: Navigate between research windows and references
- **Communication**: Switch between chat applications and tools
- **Multitasking**: Efficiently manage complex multitasking workflows

### System Administration

- **Process Management**: Monitor and manage running applications
- **Resource Monitoring**: Track application window states
- **Debugging**: Investigate window and application behavior
- **System Overview**: Get comprehensive view of system windows

## Integration with Niri

### Compositor Features

#### Window Management

- **Tiling**: Automatic window tiling and organization
- **Workspaces**: Multiple workspace support
- **Focus Management**: Sophisticated focus handling
- **Animation**: Smooth window transitions

#### Keyboard Integration

- **Niri Shortcuts**: Works alongside Niri keyboard shortcuts
- **Custom Bindings**: Configure custom key bindings
- **Focus Control**: Keyboard-driven window focus
- **Workspace Navigation**: Keyboard workspace switching

### Advanced Usage

#### Scripting Integration

```bash
# Get focused window ID
focused_id=$(niri msg --json windows | jq '.[] | select(.focused) | .id')

# Focus specific window
niri msg action focus-window --id $window_id

# Close all windows of specific app
niri msg --json windows | jq '.[] | select(.app_id == "firefox") | .id' | \
while read id; do
    niri msg action close-window --id $id
done
```

## Troubleshooting

### Common Issues

1. **No Windows Listed**: Check Niri IPC accessibility and permissions
2. **Focus Not Working**: Verify Niri msg commands work from terminal
3. **Slow Updates**: Check system performance and refresh interval
4. **Icons Missing**: Verify icon theme and application desktop files

### Niri Integration Issues

#### IPC Problems

```bash
# Test Niri IPC manually
niri msg --json windows

# Check Niri status
systemctl --user status niri

# Verify Niri configuration
niri validate-config
```

#### Permission Issues

```bash
# Check if user can execute niri commands
which niri
niri msg --help

# Verify socket permissions
ls -la /run/user/$UID/niri*
```

### Performance Issues

- **Slow Refresh**: Increase refresh interval for better performance
- **Memory Usage**: Monitor memory consumption with many windows
- **Search Performance**: Limit results for large window counts
- **System Load**: Monitor system impact of frequent updates

## Limitations

- Requires Niri compositor (not compatible with other compositors)
- Depends on Niri IPC availability and functionality
- Limited to Niri-supported window operations
- No support for X11-specific window managers
- Refresh rate limited by Niri response time
- Window icons depend on desktop file availability

## Future Enhancements

### Planned Features

- **Window Thumbnails**: Preview images of window contents
- **Advanced Filtering**: More sophisticated filter options
- **Custom Actions**: User-defined window actions
- **Workspace Management**: Enhanced workspace operations
- **Window Groups**: Group related windows together
- **History Tracking**: Track window focus history
- **Hotkey Integration**: Custom hotkey bindings for actions
