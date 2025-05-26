# Vibe Apps

A collection of vibe-coded, keyboard-centric, minimalist GTK4/Adwaita applications built with Python and Nix.

## Applications

### Bookmarks

A fast Firefox bookmarks browser with search functionality and keyboard navigation.

![Bookmarks](bookmarks/screenshot.png)

### Chat

A chat interface for OpenAI's API with markdown rendering support and streaming responses.

![Chat](chat/screenshot.png)

### Dataset Viewer (ds)

A simple command-line tool for viewing image/caption datasets pairs.

![Dataset Viewer](dataset-viewer/screenshot.png)

### Launcher

A minimalist application launcher with search functionality and launch history tracking.

![Launcher](launcher/screenshot.png)

### Music

A minimalist music player with library management and queue functionality.

![Music](music/screenshot.png)

### Notes

A markdown note-taking application with wiki-links support and live preview.

![Notes](notes/screenshot.png)

### Nix Packages

A simple interface to query and browser nix packages.

![Nix Packages](nix-packages/screenshot.png)

### Scratchpad Calculator

An interactive scratchpad calculator, similar to Soulver. (Work in Progress)

![Scratchpad](scratchpad/screenshot.png)

### WebKit Shell

A minimal web browser shell for wrapping web applications in GTK windows.

![Webkit Shell](webkit-shell/screenshot.png)

### Utilities

- **md2html**: A markdown to HTML converter with support for GFM, wiki-links, and syntax highlighting. Used by Chat and Notes.
- **raise-or-open-url**: A utility to raise existing windows or open new ones based on URLs (niri, brotab)

# Running and installing

Add the input to your flake or run with nix:

```bash
# Run specific apps
nix run https://github.com/knoopx/vibeapps/archive/refs/heads/main.zip#bookmarks
nix run https://github.com/knoopx/vibeapps/archive/refs/heads/main.zip#notes
nix run https://github.com/knoopx/vibeapps/archive/refs/heads/main.zip#launcher
nix run https://github.com/knoopx/vibeapps/archive/refs/heads/main.zip#chat
```
