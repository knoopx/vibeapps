# Notes

## Overview

A powerful markdown-based note-taking application with real-time preview, advanced search capabilities, and seamless file management. Perfect for organizing thoughts, documentation, and knowledge management.

## Features

- **Markdown Editing**: Full markdown support with syntax highlighting
- **Live Preview**: Real-time HTML preview alongside editing
- **Fast Search**: Instant search across all notes with fuzzy matching
- **File Management**: Create, rename, delete, and organize notes
- **Sidebar Navigation**: Quick access to all notes with filtering
- **External Editor Integration**: Open notes in your preferred editor
- **Keyboard Shortcuts**: Efficient keyboard-driven workflow
- **Auto-save**: Automatic saving of changes
- **Context Menus**: Right-click actions for note management

## Usage

### Basic Operations

#### Creating Notes
1. **Search/Create Bar**: Type a note name that doesn't exist
2. **Press Enter**: Creates a new note with that name
3. **Start Editing**: Immediately begin writing in markdown

#### Editing Notes
1. **Select Note**: Click on a note in the sidebar
2. **Edit Mode**: Click the edit button or press a key to start editing
3. **Preview Mode**: View rendered markdown output
4. **Save**: Changes auto-save automatically

#### Searching Notes
1. **Search Bar**: Type to search note titles and content
2. **Fuzzy Search**: Finds notes with partial matches
3. **Real-time Filter**: Results update as you type
4. **Quick Access**: Navigate to notes instantly

### Keyboard Shortcuts

#### Global Shortcuts
- **Ctrl+B**: Toggle sidebar visibility
- **Ctrl+J**: Show context menu for current note
- **Escape**: Return to search/create bar
- **Enter**: Create new note or navigate to selected note

#### Note Management
- **Edit Mode**: Start typing to enter edit mode
- **Save**: Ctrl+S (auto-save enabled)
- **External Editor**: Open in system editor

#### Navigation
- **Arrow Keys**: Navigate through note list
- **Page Up/Down**: Quick navigation through long lists
- **Home/End**: Jump to first/last note

### File Structure

Notes are stored as markdown files in:
```
~/.local/share/notes/
├── note1.md
├── project-ideas.md
├── meeting-notes.md
└── daily-journal.md
```

## Features in Detail

### Markdown Support

#### Standard Markdown
- **Headers**: # ## ### #### ##### ######
- **Emphasis**: *italic* **bold** ***bold italic***
- **Lists**: Ordered and unordered lists
- **Links**: [link text](URL)
- **Images**: ![alt text](image URL)
- **Code**: `inline code` and ```code blocks```
- **Quotes**: > blockquotes
- **Tables**: Full table support
- **Horizontal Rules**: ---

#### Extended Features
- **Strikethrough**: ~~strikethrough text~~
- **Task Lists**: - [ ] unchecked - [x] checked
- **Line Breaks**: Proper line break handling
- **Escaping**: Backslash escaping for special characters

### Search and Navigation

#### Search Capabilities
- **Title Search**: Finds notes by title
- **Content Search**: Searches within note content
- **Fuzzy Matching**: Approximate string matching
- **Real-time Results**: Updates as you type
- **Case Insensitive**: Ignores case differences

#### Navigation Features
- **Sidebar Toggle**: Show/hide note list
- **Quick Switching**: Jump between notes rapidly
- **Recent Notes**: Access recently edited notes
- **Filtered Lists**: Search narrows visible notes

### File Management

#### Note Operations
- **Create**: New notes from search bar
- **Rename**: Rename existing notes
- **Delete**: Remove notes safely
- **External Edit**: Open in system editor

#### Context Menu Actions
- **Open with Editor**: Launch external editor
- **Rename Note**: Change note title/filename
- **Delete Note**: Remove note with confirmation

### Interface Layout

#### Split View Design
- **Sidebar**: Collapsible note list and search
- **Main Area**: Note content and editing interface
- **Header**: Search bar and navigation controls
- **Responsive**: Adapts to different window sizes

#### Modern UI Elements
- **Adwaita Design**: Native GNOME appearance
- **Dark Mode Support**: Follows system theme
- **Smooth Animations**: Polished user experience
- **Touch Support**: Works with touch interfaces

## Technical Details

### Architecture

- **Frontend**: GTK4 with Adwaita design system
- **Text Editing**: GtkSourceView for markdown editing
- **Preview**: WebKit for HTML rendering
- **File Handling**: Python pathlib for robust file operations
- **Settings**: GSettings for configuration persistence

### Storage

#### File Format
- **Markdown Files**: Standard .md extension
- **UTF-8 Encoding**: Full unicode support
- **Cross-platform**: Compatible with other markdown editors
- **Version Control**: Works with git and other VCS

#### Settings Storage
- **GSettings Schema**: net.knoopx.notes
- **Sidebar State**: Remembers sidebar visibility
- **Window State**: Restores window size and position
- **User Preferences**: Persistent application settings

### Dependencies

- `gi` (PyGObject) for GTK interface
- `GtkSourceView` for syntax highlighting
- `WebKit` for markdown preview
- `pathlib` for file system operations
- `datetime` for timestamps

## Configuration

### Settings

The application uses GSettings for configuration:

#### Schema: net.knoopx.notes
- **Sidebar visibility**: Toggle state persistence
- **Window geometry**: Size and position
- **Editor preferences**: Font and appearance settings

### File Locations

#### Notes Directory
```bash
~/.local/share/notes/
```

#### Settings
```bash
# View current settings
gsettings list-recursively net.knoopx.notes

# Reset settings
gsettings reset-recursively net.knoopx.notes
```

## Use Cases

### Personal Knowledge Management

- **Daily Journal**: Capture daily thoughts and activities
- **Project Notes**: Organize project-related information
- **Learning Notes**: Document learning and research
- **Ideas Collection**: Capture and develop ideas

### Professional Use

- **Meeting Notes**: Record meeting discussions and action items
- **Documentation**: Create and maintain documentation
- **Task Planning**: Plan and track tasks and projects
- **Knowledge Base**: Build team knowledge repositories

### Development

- **Code Snippets**: Store useful code examples
- **API Documentation**: Document APIs and interfaces
- **Project Plans**: Plan development projects
- **Bug Reports**: Track and document issues

## Integration

### External Editors

Open notes in your preferred editor:
- **VS Code**: Rich markdown editing with extensions
- **Vim/Neovim**: Powerful text editing capabilities
- **Emacs**: Org-mode and markdown-mode support
- **Atom**: Markdown preview and editing features

### Version Control

Notes work seamlessly with version control:
```bash
cd ~/.local/share/notes
git init
git add .
git commit -m "Initial notes"
```

### Export and Sync

- **Backup**: Regular backup of notes directory
- **Sync**: Cloud sync via Dropbox, Google Drive, etc.
- **Export**: Convert to other formats using pandoc
- **Import**: Import existing markdown files

## Troubleshooting

### Common Issues

1. **Notes Not Saving**: Check file permissions in notes directory
2. **Search Not Working**: Verify notes directory exists and is readable
3. **Preview Not Loading**: Ensure WebKit is properly installed
4. **External Editor**: Check default application associations

### File System Issues

- **Permissions**: Ensure read/write access to notes directory
- **Disk Space**: Check available disk space for new notes
- **File Conflicts**: Handle concurrent editing carefully
- **Backup**: Regular backup prevents data loss

### Performance

- **Large Collections**: Performance scales well with many notes
- **File Size**: Large individual notes may slow preview
- **Search Speed**: Fast search even with hundreds of notes
- **Memory Usage**: Efficient memory management

## Limitations

- Preview requires WebKit for HTML rendering
- External editor integration depends on system configuration
- Large images in notes may affect performance
- Real-time collaboration not supported
- Limited rich text formatting beyond markdown
- No built-in sync or cloud integration
