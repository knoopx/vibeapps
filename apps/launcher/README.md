# Launcher

## Overview

An intelligent application launcher with adaptive search capabilities and smart ranking based on usage patterns. Features fuzzy search, launch history tracking, and personalized application suggestions.

## Features

- **Fuzzy Search**: Find applications with partial or approximate matches
- **Smart Ranking**: Applications ranked by usage frequency and search patterns
- **Launch History**: Tracks which apps you launch for different search terms
- **Adaptive Learning**: Improves suggestions based on your usage patterns
- **Fast Access**: Quick keyboard-driven interface
- **Desktop Integration**: Reads system .desktop files for comprehensive app detection
- **Icon Support**: Displays application icons when available
- **Keyboard Navigation**: Full keyboard control for efficient operation

## Usage

### Basic Search

1. **Launch**: Start the launcher application
2. **Type**: Begin typing an application name
3. **Navigate**: Use arrow keys to select from results
4. **Launch**: Press Enter to open the selected application

### Search Patterns

#### Exact Matching
```
firefox → Mozilla Firefox
calculator → Calculator
```

#### Fuzzy Search
```
fx → Firefox
calc → Calculator
term → Terminal
code → Visual Studio Code
```

#### Partial Matching
```
chrome → Google Chrome
office → LibreOffice applications
media → Media players
```

### Keyboard Shortcuts

- **Type**: Start searching immediately
- **↑/↓**: Navigate through results
- **Enter**: Launch selected application
- **Escape**: Close launcher
- **Tab**: Cycle through results
- **Ctrl+Q**: Quit launcher

## Features in Detail

### Smart Ranking Algorithm

The launcher uses sophisticated ranking based on:

1. **Search Term History**: Remembers which apps you chose for specific searches
2. **Launch Frequency**: More frequently used apps rank higher
3. **Fuzzy Match Quality**: Better text matches get priority
4. **Recent Usage**: Recently launched apps get slight boost
5. **Context Awareness**: Considers current search patterns

### Adaptive Learning

#### How It Works

- **Pattern Recognition**: Tracks search terms and resulting launches
- **Frequency Counting**: Maintains counters for term-app pairs
- **Ranking Adjustment**: Adjusts future results based on history
- **Personalization**: Adapts to individual usage patterns

#### Example Learning

```
Search: "edit" → Launch: Visual Studio Code (3 times)
Search: "edit" → Launch: Gedit (1 time)

Future "edit" searches will prioritize Visual Studio Code
```

### Data Storage

#### History File Location
```
~/.local/share/net.knoopx.launcher/history.json
```

#### Data Structure
```json
{
  "search_term": {
    "app_id": launch_count,
    "another_app_id": launch_count
  }
}
```

### Application Detection

#### Desktop File Sources

The launcher scans for .desktop files in:
- `/usr/share/applications/`
- `/usr/local/share/applications/`
- `~/.local/share/applications/`
- `$XDG_DATA_DIRS/applications/`

#### Application Information

Extracts from .desktop files:
- **Name**: Application display name
- **Description**: App description for context
- **Icon**: Application icon path
- **Executable**: Command to launch
- **Categories**: Application categories
- **Keywords**: Additional search terms

## Technical Details

### Architecture

- **Frontend**: GTK4 with Adwaita design
- **Search Engine**: Custom fuzzy matching algorithm
- **Data Persistence**: JSON-based history storage
- **Desktop Integration**: FreeDesktop .desktop file parsing
- **Threading**: Background operations for responsive UI

### Search Algorithm

#### Fuzzy Matching Features

1. **Substring Matching**: Finds partial matches anywhere in the name
2. **Character Sequence**: Matches character sequences in order
3. **Word Boundary**: Prioritizes matches at word boundaries
4. **Case Insensitive**: Ignores case differences
5. **Acronym Support**: Matches first letters of words

#### Ranking Factors

```python
score = base_match_score + history_boost + frequency_factor
```

- **Base Score**: Quality of text match (0-100)
- **History Boost**: Previous launches for this search term
- **Frequency Factor**: Overall application usage frequency

### Performance Optimizations

- **Lazy Loading**: Desktop files parsed on demand
- **Caching**: Application list cached between searches
- **Background Updates**: History updates don't block UI
- **Memory Efficient**: Minimal memory footprint

## Configuration

### History Management

The launcher automatically:
- Creates history file on first run
- Updates history after each launch
- Handles file permissions gracefully
- Provides fallback behavior for read-only environments

### Customization Options

While the launcher works out-of-the-box, you can:
- Clear history by deleting the history file
- Backup/restore history for consistency across systems
- Monitor history file for usage analytics

## Use Cases

### Daily Workflow

- **Quick Access**: Launch frequently used applications
- **Discovery**: Find applications by approximate names
- **Efficiency**: Reduce time spent navigating menus
- **Personalization**: Adapts to your specific workflow

### Power User Features

- **Fuzzy Search**: Type partial names for quick access
- **Pattern Learning**: Builds personalized shortcuts
- **Keyboard-Only**: Complete operation without mouse
- **Fast Switching**: Quick application switching

## Troubleshooting

### Common Issues

1. **No Results**: Check if desktop files are properly installed
2. **Slow Response**: Large application lists may cause delays
3. **Missing Icons**: Some applications may not have proper icon files
4. **History Not Saving**: Check write permissions for data directory

### Performance Tips

- **Clear History**: Periodically clear history for fresh ranking
- **Check Desktop Files**: Ensure applications have proper .desktop files
- **Memory Usage**: Monitor for large application lists
- **File Permissions**: Ensure proper access to data directories

## Limitations

- Requires applications to have .desktop files for detection
- History tracking requires write access to user data directory
- Fuzzy search quality depends on application naming consistency
- Does not launch system commands or arbitrary executables
- Limited to GUI applications with desktop integration
