# Bookmarks Browser

A GTK4/libadwaita application for browsing and searching Firefox bookmarks using `foxmarks`.

## Features

- **Fast bookmark search**: Type to filter bookmarks by title or URL
- **Keyboard navigation**: Arrow keys to navigate, Enter to open, Escape to quit
- **Automatic Firefox profile detection**: Finds and uses your default Firefox profile
- **Modern UI**: Built with GTK4 and libadwaita for native Linux desktop integration

## Usage

```bash
# Run the application
nix --offline run path:.#bookmarks
```

## How it works

The application uses the `foxmarks` tool to read Firefox bookmarks from your browser's database. It automatically detects your Firefox profile and loads all bookmarks into a searchable interface.

### Keyboard shortcuts

- **Type**: Filter bookmarks by title or URL
- **↑/↓**: Navigate through results
- **Enter**: Open selected bookmark in default browser
- **Escape**: Quit application

## Dependencies

- GTK4 and libadwaita for the UI
- `foxmarks` for reading Firefox bookmarks
- Python 3.12 with PyGObject

## Profile Detection

The application tries to find your Firefox profile in this order:
1. `~/.mozilla/firefox/knoopx`
2. `~/.mozilla/firefox/default`
3. `~/.mozilla/firefox/default-release`
4. Any directory containing `places.sqlite`

If automatic detection fails, `foxmarks` will attempt to use its own default profile detection.
