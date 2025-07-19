# File Picker

A simple, fast libadwaita/GTK4 application for selecting files from grouped lists provided via stdin. Designed for integration into scripts and workflows, File Picker displays files in visually distinct groups and allows users to select multiple files using checkboxes. Selected files are printed to stdout for easy downstream processing.

## Features

- Grouped file display: visually separates files into groups as provided by input
- Multi-selection: select any number of files using checkboxes
- Keyboard navigation: supports keyboard shortcuts for quick selection and navigation
- Responsive UI: built with libadwaita/GTK4 for a modern, adaptive interface
- Output: prints selected files to stdout and exits cleanly
- Script-friendly: works seamlessly with shell pipelines and automation

## Usage

Pipe groups of files separated by blank lines (fdupes format, one file per line) to the app:

```sh
cat filelist.txt | file-picker
```

- Each group of files should be separated by a blank line.
- The app will display each group in its own section.
- Use the checkboxes to select files, then confirm selection to print the selection to stdout.

### Example filelist.txt

```
fileA.txt
fileB.txt

fileC.txt
fileD.txt
```

## Packaging

Packaged with Nix for reproducible builds and easy deployment. See [`file-picker.nix`](file-picker.nix) for details on dependencies and build instructions.

## Requirements

- Python 3.10+
- GTK4 and libadwaita Python bindings
- Nix (for packaging)

## Screenshots

See the repository for screenshots of the UI.
