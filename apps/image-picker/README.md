# Image Picker

A simple, fast libadwaita/GTK4 application for selecting images from grouped lists provided via stdin. Designed for integration into scripts and workflows, Image Picker displays images in visually distinct groups, with each group shown as a row containing a grid of image thumbnails. Users can select multiple images using checkboxes. Selected images are printed to stdout for easy downstream processing.

## Features

- Grouped image display: visually separates images into groups as provided by input
- Grid layout: each group is shown as a row with a grid of image thumbnails
- Multi-selection: select any number of images using checkboxes
- Quick selection menu: use the menu button in the header bar to instantly select all, unselect all, invert selection, or select/unselect images by path, date, size, name length, image dimensions, or first/last in group
- Keyboard navigation: supports keyboard shortcuts for quick selection and navigation
- Responsive UI: built with libadwaita/GTK4 for a modern, adaptive interface
- Output: prints selected images to stdout and exits cleanly
- Script-friendly: works seamlessly with shell pipelines and automation

## Usage

Pipe groups of image file paths separated by blank lines (fdupes format, one file per line) to the app:

```sh
cat imagelist.txt | image-picker
```

- Each group of images should be separated by a blank line.
- The app will display each group in its own row, with a grid of image thumbnails.
- Use the checkboxes to select images, or use the quick selection menu in the header bar to select all, unselect all, or invert selection instantly. Then confirm selection to print the selection to stdout.

### Example imagelist.txt

```
imageA.png
imageB.jpg

imageC.png
imageD.jpg
```

## Packaging

Packaged with Nix for reproducible builds and easy deployment. See [`image-picker.nix`](image-picker.nix) for details on dependencies and build instructions.

## Requirements

- Python 3.10+
- GTK4 and libadwaita Python bindings
- Nix (for packaging)

## Screenshots

See the repository for screenshots of the UI.
