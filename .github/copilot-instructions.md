# Instructions for LLM Agents

## Special Considerations when running shell commands in VSCode terminal

When running shell commands in the VSCode terminal, keep in mind the following:

The VSCode terminal is running Fish shell. You cannot run commands that span multiple lines like:

```bash
python -c "
# This is a multi-line command
print('Hello, World!')
"
```

either use a single line command, run an interactive python repl or create a temporary script file to execute multi-line commands.


## System Overview

This is a **NixOS 25.11 (Xantusia)** system running on **Intel i7-11700K** (8 cores, 16 threads) with **32GB RAM**. The system uses:

- **Desktop Environment**: niri (Wayland compositor)
- **Shell**: Fish 4.0.2
- **Package Manager**: Nix 2.28.3
- **Python Runtime**: 3.12.10
- **JavaScript Runtime**: Bun 1.2.14
- **Kernel**: Linux 6.14.7-zen1 (ZEN kernel)

## Repository Contents

This repository contains a collection of **minimalist GTK4/libadwaita applications** and utilities designed for keyboard-centric workflows:

### Python Applications (GTK4/libadwaita)
- **chat**: OpenAI API chat interface with markdown rendering and streaming
- **dataset-viewer** (alias: `ds`): Image/caption dataset viewer for ML workflows
- **launcher**: Fast application launcher with search and frequency tracking
- **music**: Music library browser with album management and queue system
- **notes**: Markdown note-taking with wiki-links and live preview
- **nix-packages**: Nix package repository browser and search
- **scratchpad**: Interactive mathematical calculator (Soulver-like)
- **webkit-shell**: Minimal web browser for wrapping web applications
- **reminder**: Calendar event creation interface
- **mdx-editor**: Advanced markdown editor with live React components

### JavaScript Utilities
- **md2html**: Advanced markdown to HTML converter with syntax highlighting
- **remarkDefinitionList**: Custom remark plugin for definition lists

### System Integration Tools
- **raise-or-open-url**: Smart URL/window management (integrates with Firefox + brotab + niri)

## Technical Architecture

- Applications are packaged with **Nix** for reproducible builds and dependency management
- Each application has its own `.nix` file specifying dependencies
- All applications are exported in the `flake.nix` file
- **GTK4/libadwaita** provides modern Linux desktop integration
- **WebKit** integration for rich content rendering (Chat, Notes apps)
- **Wayland** display protocol with niri compositor
- **Offline-capable** operation with locked dependencies

## Running Applications

### Python Applications

To run a Python application:

```bash
nix --offline run path:.#app_name -- arg1 arg2
```

Examples:
```bash
# Chat with initial prompt
nix --offline run path:.#chat -- "Hello, world!"

# Dataset viewer
nix --offline run path:.#dataset-viewer -- /path/to/dataset .txt

# Application launcher
nix --offline run path:.#launcher

# Music library browser
nix --offline run path:.#music

# Notes application
nix --offline run path:.#notes

# Package browser
nix --offline run path:.#nix-packages

# Calculator
nix --offline run path:.#scratchpad

# Web browser shell
nix --offline run path:.#webkit-shell -- --url "https://example.com"
```

### JavaScript Applications

Use **bun** to run JavaScript applications:

```bash
# Markdown to HTML converter
echo "# Hello" | bun run md2html/md2html.js

# Run with bun directly
bun md2html/md2html.js
```

## Testing Applications

### Python Applications

To test a Python application, navigate to the application's directory and run tests:

```bash
cd $app_name && python -m unittest test_*.py
```

Example:
```bash
cd scratchpad && python -m unittest test_calculator.py
```

### JavaScript Applications

Use **Vitest** for testing JavaScript applications:

```bash
# Run all tests
bun test

# Run specific test file
bun test remarkDefinitionList.test.js
```

Test files use the suffix `test.js` and are located in the same directory as the application.


## System Integration and Available Tools

The system includes several external tools that applications integrate with:

- **Firefox**: Web browser (`/etc/profiles/per-user/knoopx/bin/firefox`)
- **Amberol**: Music player for audio playback (`/etc/profiles/per-user/knoopx/bin/amberol`)
- **brotab (bt)**: Browser tab automation tool (`/etc/profiles/per-user/knoopx/bin/bt`)
- **niri**: Wayland compositor with message/window management API
- **xdg-open**: System file/URL opener

## Environment Details

- **Display**: Wayland (`WAYLAND_DISPLAY=wayland-1`) with X11 compatibility (`DISPLAY=:0`)
- **GTK**: Full GTK 2/3/4 support with flatpak and nix integration paths
- **Accessibility**: `GTK_A11Y=none`
- **File Systems**: 2.8TB NVMe storage (90% used), 32GB RAM, 63GB swap
