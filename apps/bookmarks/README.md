# Bookmarks

## Overview

A fast and intuitive bookmark browser that provides instant search and navigation through your Firefox bookmarks. Features automatic profile detection, context menu actions, and seamless desktop integration.

## Features

- **Instant Search**: Real-time filtering by bookmark title or URL
- **Firefox Integration**: Direct access to Firefox bookmark database
- **Automatic Profile Detection**: Finds and uses your Firefox profile automatically
- **Context Menu Actions**: Right-click for additional bookmark operations
- **Keyboard Navigation**: Full keyboard control for efficient browsing
- **Modern Interface**: GTK4 with Adwaita design for native desktop integration
- **Fast Loading**: Efficient bookmark database reading and caching
- **URL Preview**: See full URLs with proper text wrapping

## Usage

### Basic Operations

#### Searching Bookmarks

1. **Launch**: Start the bookmarks application
2. **Type**: Begin typing to filter bookmarks instantly
3. **Navigate**: Use arrow keys to browse through results
4. **Open**: Press Enter or click to open bookmarks

#### Bookmark Management

1. **Context Menu**: Right-click for additional actions
2. **Copy Operations**: Copy URLs or titles to clipboard
3. **Quick Access**: Fast navigation through large bookmark collections

### Keyboard Shortcuts

#### Navigation

- **Type**: Start filtering bookmarks immediately
- **↑/↓**: Navigate through filtered results
- **Enter**: Open selected bookmark in default browser
- **Escape**: Clear search or quit application

#### Context Actions

- **Ctrl+J**: Show context menu for selected bookmark

### Search Capabilities

#### Search Criteria

- **Title Search**: Find bookmarks by page title
- **URL Search**: Search within bookmark URLs
- **Combined Search**: Searches both title and URL simultaneously
- **Partial Matching**: Finds matches anywhere in the text

#### Search Examples

```
github → Finds GitHub-related bookmarks
python docs → Finds Python documentation
localhost → Finds local development bookmarks
tutorial → Finds tutorial pages
```

## Features in Detail

### Firefox Integration

#### Automatic Profile Detection

The application intelligently detects your Firefox profile:

1. **User-specific Profile**: `~/.mozilla/firefox/knoopx`
2. **Default Profile**: `~/.mozilla/firefox/default`
3. **Release Profile**: `~/.mozilla/firefox/default-release`
4. **Database Detection**: Any directory containing `places.sqlite`
5. **Fallback**: Uses Firefox's default profile detection

#### Database Access

- **SQLite Integration**: Direct reading from Firefox's places.sqlite
- **Safe Access**: Read-only access to prevent database corruption
- **Temporary Copies**: Creates temporary copies for safe reading
- **Concurrent Access**: Handles Firefox running simultaneously

### Context Menu Actions

#### Available Actions

- **Open Bookmark**: Launch in default browser
- **Copy URL**: Copy bookmark URL to clipboard
- **Copy Title**: Copy bookmark title to clipboard
- **View Details**: Display comprehensive bookmark information

#### Clipboard Integration

- **System Clipboard**: Full clipboard integration
- **Multiple Formats**: Copy as plain text or rich text
- **Quick Copy**: Single-click copying operations

### User Interface

#### Layout Design

- **Search Bar**: Prominent search input at top
- **Results List**: Scrollable bookmark list with details
- **Status Display**: Loading and result count indicators
- **Responsive Design**: Adapts to different window sizes

#### Visual Elements

- **Typography**: Clear title and URL display
- **Color Coding**: Distinctive styling for titles and URLs
- **Spacing**: Proper spacing for readability
- **Scrolling**: Smooth scrolling through large lists

## Technical Details

### Architecture

- **Frontend**: GTK4 with Adwaita design system
- **Database**: SQLite integration for Firefox bookmarks
- **Threading**: Background bookmark loading
- **Caching**: Efficient bookmark caching for performance

### Firefox Integration

#### Database Structure

```sql
-- Firefox bookmarks table structure
moz_bookmarks (
  id INTEGER PRIMARY KEY,
  type INTEGER,
  fk INTEGER,
  parent INTEGER,
  position INTEGER,
  title TEXT,
  keyword_id INTEGER,
  folder_type TEXT,
  dateAdded INTEGER,
  lastModified INTEGER
)

moz_places (
  id INTEGER PRIMARY KEY,
  url TEXT,
  title TEXT,
  rev_host TEXT,
  visit_count INTEGER,
  hidden INTEGER,
  typed INTEGER,
  frecency INTEGER,
  last_visit_date INTEGER,
  guid TEXT
)
```

#### Profile Detection Logic

```python
# Profile search order
profile_paths = [
    "~/.mozilla/firefox/knoopx",
    "~/.mozilla/firefox/default",
    "~/.mozilla/firefox/default-release",
    # Scan for places.sqlite in any profile
]
```

### Performance Optimizations

#### Loading Strategy

- **Background Loading**: Non-blocking bookmark retrieval
- **Incremental Search**: Fast filtering without re-reading database
- **Memory Caching**: Cache bookmarks in memory for instant search
- **Lazy Loading**: Load bookmark details on demand

#### Search Optimization

- **Case-Insensitive**: Efficient case-insensitive searching
- **Substring Matching**: Fast substring matching algorithms
- **Result Limiting**: Limit displayed results for performance
- **Search Debouncing**: Optimize search frequency

## Configuration

### File Locations

#### Firefox Profiles

```bash
~/.mozilla/firefox/
├── profiles.ini          # Profile configuration
├── knoopx/              # User-specific profile
├── default/             # Default profile
└── default-release/     # Release profile
```

#### Database Files

```bash
~/.mozilla/firefox/[profile]/
├── places.sqlite        # Bookmarks and history
├── favicons.sqlite      # Bookmark icons
└── prefs.js            # Profile preferences
```

### Environment Variables

- **FIREFOX_PROFILE**: Override automatic profile detection
- **XDG_CONFIG_HOME**: Custom configuration directory location

## Use Cases

### Daily Browsing

- **Quick Access**: Instantly find frequently used bookmarks
- **Research**: Navigate through research bookmark collections
- **Development**: Access development resources and documentation
- **Reference**: Quick lookup of reference materials

### Bookmark Management

- **Organization**: Browse bookmark collections efficiently
- **Cleanup**: Identify and manage bookmark collections
- **Search**: Find specific bookmarks in large collections
- **Access**: Quick access without opening full browser

### Development Workflow

- **Documentation**: Quick access to API documentation
- **Tools**: Access development tools and utilities
- **Resources**: Navigate through development resources
- **References**: Quick lookup of code examples and tutorials

## Integration

- **Default Browser**: Opens bookmarks in system default browser
- **URL Handling**: Proper URL protocol handling
- **External Links**: Seamless external link management

## Troubleshooting

### Common Issues

1. **No Bookmarks Found**: Check Firefox profile detection and database permissions
2. **Slow Loading**: Large bookmark collections may require patience
3. **Search Not Working**: Verify bookmark database accessibility
4. **Profile Detection Failed**: Check Firefox profile directory structure

### Profile Issues

#### Manual Profile Selection

```bash
# Check available profiles
ls ~/.mozilla/firefox/

# Verify places.sqlite exists
ls ~/.mozilla/firefox/[profile]/places.sqlite
```

#### Permission Issues

```bash
# Check database permissions
ls -la ~/.mozilla/firefox/[profile]/places.sqlite

# Ensure read access
chmod 644 ~/.mozilla/firefox/[profile]/places.sqlite
```

### Performance Issues

- **Large Collections**: Consider Firefox bookmark organization
- **Memory Usage**: Monitor memory usage with many bookmarks
- **Search Speed**: Large bookmark sets may slow search
- **Database Locks**: Ensure Firefox is not blocking database access

## Limitations

- Read-only access to Firefox bookmarks (no editing)
- Requires Firefox bookmark database access
- Limited to Firefox bookmarks (no Chrome, Safari, etc.)
- No bookmark synchronization or backup features
- Depends on Firefox profile structure
- No real-time bookmark updates from Firefox

## Future Enhancements

### Planned Features

- **Webpage preview**: display a preview of the bookmark
- **Multiple Browser Support**: Chrome, Safari bookmark integration
- **Bookmark Editing**: Add, edit, delete bookmark functionality
- **Custom Database**: Independent bookmark storage system
- **Tag Support**: Bookmark tagging and organization
- **Export/Import**: Backup and restore functionality
- **Sync Integration**: Cloud synchronization support
  - built-in bookmarking (just paste link in search entry)
    - scrapes websites and summarizes it using openai
    - screenshots it (using firefox)
    - shows notification after scraping
