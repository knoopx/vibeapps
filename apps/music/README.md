# Music

## Overview

A sophisticated music library manager with intelligent scanning, collection management, and advanced filtering capabilities. Features automatic metadata extraction, custom collections, star ratings, and efficient organization of large music libraries.

## Features

- **Intelligent Scanning**: Automatic music directory scanning with metadata extraction
- **Collection Management**: Create and manage custom music collections
- **Star Ratings**: Rate and filter music by star ratings
- **Advanced Search**: Powerful search across titles, artists, albums, and metadata
- **Context Menus**: Rich context menu actions for music management
- **Real-time Filtering**: Instant filtering with multiple criteria
- **Metadata Integration**: Reads .nfo files and music metadata
- **Genre Classification**: Automatic genre detection and classification
- **Progress Tracking**: Visual progress indicators for scanning operations

## Usage

### Basic Operations

#### Library Scanning
1. **Initial Scan**: First launch automatically scans your music directory
2. **Refresh**: Use Ctrl+R to refresh the music library
3. **Progress**: Monitor scanning progress with the circular progress indicator
4. **Background**: Scanning continues in the background while browsing

#### Searching and Filtering
1. **Search Bar**: Type to search across all music metadata
2. **Star Filter**: Use Ctrl+S to toggle starred music filter
3. **Collection Filter**: Select specific collections to filter by
4. **Combined Filters**: Use multiple filters simultaneously

#### Music Management
1. **Star Rating**: Click star buttons to rate music
2. **Collections**: Add music to custom collections
3. **Context Menu**: Right-click for additional actions
4. **Metadata View**: View detailed music information

### Keyboard Shortcuts

#### Navigation and Search
- **Type**: Start searching immediately
- **↑/↓**: Navigate through music list
- **Enter**: Play or view selected music
- **Escape**: Clear search filters

#### Quick Actions
- **Ctrl+S**: Toggle starred music filter
- **Ctrl+R**: Refresh music library
- **Ctrl+J**: Show context menu for selected item
- **Space**: Quick preview or play

#### Collection Management
- **Ctrl+C**: Add to collection
- **Ctrl+Shift+C**: Manage collections
- **Alt+1-9**: Quick access to numbered collections

### Collection System

#### Built-in Collections
The app supports automatic collection creation based on metadata:
- **Genre Collections**: Metal, Punk, Jazz, Folk, etc.
- **Label Collections**: Blue Note, Colmine, etc.
- **Style Collections**: Hardcore, Post-Hardcore, Mathrock, etc.
- **Era Collections**: By decade or time period

#### Custom Collections
```bash
# Example collection creation commands
find . -type f -iname '*.nfo' -exec grep -l -i "screamo" {} + | \
xargs -n1 dirname | xargs -n1 basename | \
jq -R 'ascii_downcase' | jq -s . > \
~/.config/net.knoopx.music/collections/Screamo.json
```

#### Collection File Format
```json
[
  "artist name - album name",
  "another artist - another album",
  "compilation album title"
]
```

## Features in Detail

### Music Scanning

#### Automatic Discovery
- **File Format Support**: MP3, FLAC, OGG, M4A, and other common formats
- **Directory Structure**: Handles various organization patterns
- **Metadata Reading**: Extracts ID3 tags and other metadata
- **NFO File Support**: Reads .nfo files for additional information
- **Recursive Scanning**: Scans subdirectories automatically

#### Metadata Extraction
- **Basic Tags**: Title, artist, album, year, genre
- **Extended Tags**: Label, catalog number, release type
- **File Information**: Bitrate, duration, file size
- **Cover Art**: Album artwork extraction and display
- **Custom Fields**: Additional metadata from .nfo files

### Collection Management

#### Collection Creation
- **Manual Creation**: Create collections through the interface
- **Automatic Generation**: Generate collections based on metadata
- **Import/Export**: Import collections from files
- **Batch Operations**: Mass collection management

#### Collection Types
- **Genre-based**: Collections organized by musical genre
- **Label-based**: Collections organized by record label
- **Artist-based**: Collections focused on specific artists
- **Custom**: User-defined collections with custom criteria

### Filtering and Search

#### Search Capabilities
- **Full-text Search**: Search across all metadata fields
- **Field-specific**: Search specific fields like artist or album
- **Boolean Logic**: Use AND, OR, NOT operators
- **Regular Expressions**: Advanced pattern matching
- **Fuzzy Matching**: Find approximate matches

#### Filter Types
- **Star Rating**: Filter by star ratings (1-5 stars)
- **Collection**: Filter by collection membership
- **Genre**: Filter by musical genre
- **Year**: Filter by release year
- **Format**: Filter by audio format

### User Interface

#### Layout Components
- **Header Bar**: Search, collections, and filter controls
- **Music List**: Scrollable list of music with details
- **Side Panel**: Collection browser and filters
- **Status Bar**: Progress indicators and status messages
- **Context Menus**: Right-click actions and operations

#### Visual Elements
- **Star Ratings**: Interactive star rating display
- **Progress Indicators**: Circular progress for operations
- **Badges**: Visual indicators for status and metadata
- **Typography**: Clear, readable text with proper hierarchy

## Technical Details

### Architecture

- **Frontend**: GTK4 with Adwaita design system
- **Backend**: Python with music metadata libraries
- **Storage**: JSON-based collections and SQLite caching
- **Threading**: Background scanning and operations
- **Configuration**: GSettings for user preferences

### File Structure

#### Music Directory Layout
```
~/Music/
├── Artist Name/
│   ├── Album Name/
│   │   ├── 01 Track Name.mp3
│   │   ├── 02 Another Track.mp3
│   │   └── album.nfo
│   └── Another Album/
└── Various Artists/
```

#### Configuration Directory
```
~/.config/net.knoopx.music/
├── collections/
│   ├── Screamo.json
│   ├── Metal.json
│   └── Jazz.json
├── starred.json
└── cache.db
```

### Dependencies

- `gi` (PyGObject) for GTK interface
- `mutagen` for music metadata reading
- `pathlib` for file system operations
- `json` for collection storage
- `threading` for background operations

### Music Scanning Process

#### Scanning Workflow
1. **Directory Traversal**: Recursively scan music directory
2. **File Detection**: Identify music files by extension
3. **Metadata Extraction**: Read tags and file information
4. **NFO Processing**: Parse .nfo files for additional data
5. **Database Update**: Update internal database with new information
6. **Collection Update**: Update relevant collections

#### Performance Optimization
- **Incremental Scanning**: Only scan changed files
- **Background Processing**: Non-blocking UI during scans
- **Caching**: Cache metadata for faster subsequent access
- **Batch Operations**: Process multiple files efficiently

## Configuration

### Settings Schema

#### GSettings: net.knoopx.music
- **music-directory**: Path to music library
- **scan-frequency**: Automatic scan interval
- **default-collections**: Collections to load by default
- **star-filter-enabled**: Default star filter state
- **window-geometry**: Window size and position

### Collection Commands

#### Genre Collection Creation
```bash
# Metal collection
find . -type f -iname '*.nfo' -exec grep -l -i "metal" {} + | \
xargs -n1 dirname | xargs -n1 basename | \
jq -R 'ascii_downcase' | jq -s . > \
~/.config/net.knoopx.music/collections/Metal.json

# Jazz collection
find . -type f -iname '*.nfo' -exec grep -l -i "jazz" {} + | \
xargs -n1 dirname | xargs -n1 basename | \
jq -R 'ascii_downcase' | jq -s . > \
~/.config/net.knoopx.music/collections/Jazz.json
```

#### Label Collection Creation
```bash
# Blue Note Records
find . -type f -iname '*.nfo' -exec grep -l -i "blue note" {} + | \
xargs -n1 dirname | xargs -n1 basename | \
jq -R 'ascii_downcase' | jq -s . > \
~/.config/net.knoopx.music/collections/Blue Note.json
```

## Use Cases

### Music Discovery

- **Genre Exploration**: Browse music by genre collections
- **Label Discovery**: Explore music from specific record labels
- **Rating-based**: Find highly-rated music in your collection
- **Search-based**: Discover music through keyword searches

### Library Organization

- **Collection Management**: Organize music into meaningful groups
- **Star Ratings**: Rate music for future reference
- **Metadata Curation**: Maintain clean, accurate metadata
- **Duplicate Detection**: Identify and manage duplicate tracks

### Professional Use

- **DJ Libraries**: Organize music for performance use
- **Music Research**: Academic and professional music research
- **Catalog Management**: Maintain comprehensive music catalogs
- **Production Work**: Organize source material for production

## Integration

### External Tools

#### Music Players
- **VLC**: Launch music in VLC media player
- **MPV**: Play music with MPV
- **System Player**: Use default system music player

#### Metadata Tools
- **MusicBrainz**: Integration with MusicBrainz database
- **Last.fm**: Scrobbling and metadata enhancement
- **Discogs**: Album and release information

### File System Integration

- **File Manager**: Open music directories in file manager
- **External Editors**: Edit metadata with external tools
- **Backup Tools**: Integrate with backup systems
- **Cloud Sync**: Synchronize collections across devices

## Troubleshooting

### Common Issues

1. **Slow Scanning**: Large libraries may require time for initial scan
2. **Missing Metadata**: Some files may lack proper metadata tags
3. **Collection Errors**: Check JSON syntax in collection files
4. **Performance Issues**: Monitor memory usage with large libraries

### Scanning Problems

#### File Access Issues
```bash
# Check music directory permissions
ls -la ~/Music

# Verify file accessibility
find ~/Music -name "*.mp3" -not -readable
```

#### Metadata Issues
```bash
# Check NFO file format
file ~/Music/*/*.nfo

# Validate JSON collections
jq . ~/.config/net.knoopx.music/collections/*.json
```

### Performance Optimization

- **Library Size**: Consider organizing very large libraries
- **Scan Frequency**: Adjust automatic scanning intervals
- **Collection Size**: Limit collection sizes for better performance
- **Memory Usage**: Monitor application memory consumption

## Limitations

- Requires read access to music files and directories
- Collection system limited to JSON file format
- No built-in music playback (uses external players)
- Metadata editing requires external tools
- Large libraries may impact initial scanning performance
- Limited to local music files (no streaming service integration)

## Future Enhancements

### Planned Features
- **Built-in Player**: Integrated music playback capabilities
- **Metadata Editing**: In-app metadata editing tools
- **Playlist Support**: Create and manage playlists
- **Streaming Integration**: Connect to streaming services
- **Advanced Analytics**: Library statistics and analysis
- **Remote Access**: Web interface for remote library access
- **Mobile Sync**: Synchronize with mobile music apps
