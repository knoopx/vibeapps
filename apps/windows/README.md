# Windows App

A GTK4/Libadwaita application that displays a list of open windows in the Niri compositor and allows you to focus or close them.

## Features

- **Window List**: Shows all open windows with their titles, app IDs, and workspace information
- **Search**: Filter windows by title, app ID, window ID, workspace, or PID
- **Focus Windows**: Click or press Enter to focus a selected window
- **Context Menu**: Right-click for additional actions:
  - Focus Window
  - Close Window
  - Copy Window ID
  - Copy Title
- **Status Indicators**: Visual badges for focused, urgent, and floating windows
- **Auto-refresh**: Updates the window list every 5 seconds
- **App Icons**: Shows appropriate icons for recognized applications

## Usage

The app uses the `niri msg --json windows` command to get the list of windows and `niri msg action focus-window --id <id>` to focus windows.

### Keyboard Shortcuts

- **Enter**: Focus selected window
- **Escape**: Close the app
- **Ctrl+J**: Open context menu (if enabled)

### Search

You can search for windows by:
- Window title
- Application ID
- Window ID
- Workspace ID
- Process ID

## Dependencies

- GTK4
- Libadwaita
- Python 3
- Niri compositor

## Implementation

The app extends the `PickerWindow` base class and implements:
- `WindowItem`: Data model for window information
- `WindowsWindow`: Main application window with search and list functionality
- Integration with Niri compositor for window management
