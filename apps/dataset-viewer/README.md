# Dataset Viewer

## Overview

A specialized image and caption dataset viewer designed for machine learning workflows. Browse through image datasets with corresponding text captions, edit captions in real-time, and navigate efficiently through large collections.

## Features

- **Image Display**: High-quality image rendering with automatic scaling
- **Caption Editing**: Live editing of text captions with immediate saving
- **Keyboard Navigation**: Fast browsing through datasets
- **Multiple Caption Formats**: Support for various caption file extensions
- **Auto-save**: Automatic saving of caption changes
- **Responsive Layout**: Adaptive interface that works with different screen sizes
- **Large Dataset Support**: Efficient handling of thousands of images

## Supported Formats

### Image Formats

- **JPEG/JPG**: Standard JPEG images
- **PNG**: Portable Network Graphics
- **GIF**: Graphics Interchange Format
- **BMP**: Bitmap images
- **TIFF**: Tagged Image File Format
- **WEBP**: Modern web image format

### Caption Formats

- **TXT**: Plain text files (.txt)
- **CAPTION**: Caption files (.caption)
- **Custom Extensions**: Configurable caption file extensions

## Usage

### Command Line

```bash
# Basic usage with default .txt extension
python dataset-viewer.py /path/to/dataset

# Specify custom caption extension
python dataset-viewer.py /path/to/dataset --caption-ext .caption

# Example with specific dataset
python dataset-viewer.py ~/datasets/my_images --caption-ext .txt
```

### Arguments

- **dataset_dir**: Path to directory containing images and captions
- **--caption-ext**: File extension for caption files (default: .txt)

### Navigation

#### Keyboard Shortcuts

- **Arrow Left/Right**: Navigate between images
- **Page Up/Down**: Jump through images quickly
- **Home**: Go to first image
- **End**: Go to last image
- **Ctrl+S**: Save current caption (auto-saves enabled by default)

#### Mouse Navigation

- **Click image**: Focus on image area
- **Click text area**: Edit captions
- **Scroll wheel**: Navigate through images

### Dataset Structure

Your dataset should be organized as follows:

```
dataset/
├── image001.jpg
├── image001.txt
├── image002.jpg
├── image002.txt
├── image003.png
├── image003.txt
└── ...
```

### Caption Editing

1. **Select Text Area**: Click in the caption text field
2. **Edit Content**: Type or modify the caption text
3. **Auto-save**: Changes are automatically saved
4. **Navigation**: Use keyboard shortcuts to move between images

## Features in Detail

### Image Handling

- **Automatic Scaling**: Images are scaled to fit the viewing area
- **Aspect Ratio Preservation**: Original proportions maintained
- **Quality Optimization**: Efficient rendering for large images
- **Format Support**: Wide range of image formats supported

### Caption Management

- **Live Editing**: Edit captions directly in the interface
- **Automatic Saving**: Changes saved immediately upon modification
- **File Synchronization**: Caption files updated in real-time
- **Undo Support**: Standard text editing features available

### Performance

- **Lazy Loading**: Images loaded on demand for better performance
- **Memory Management**: Efficient memory usage for large datasets
- **Responsive Navigation**: Fast switching between images
- **Background Operations**: Non-blocking file operations

## Technical Details

### Architecture

- **Frontend**: GTK4 with Adwaita design system
- **Image Rendering**: Gtk.Picture for optimized display
- **Text Editing**: Gtk.TextView with automatic saving
- **File Management**: Python pathlib for robust file handling

### Dependencies

- `gi` (PyGObject) for GTK interface
- `pathlib` for file system operations
- `os` and `sys` for system integration

### File Detection

The application automatically:
- Scans directories for supported image formats
- Matches images with corresponding caption files
- Handles missing caption files gracefully
- Supports custom caption file extensions

## Use Cases

### Machine Learning

- **Dataset Preparation**: Review and edit training data
- **Quality Control**: Verify image-caption pairs
- **Data Cleaning**: Correct mislabeled or inaccurate captions
- **Dataset Exploration**: Browse through large collections efficiently

### Content Management

- **Image Cataloging**: Organize image collections with descriptions
- **Metadata Editing**: Update image descriptions and tags
- **Content Review**: Quality assurance for image datasets
- **Batch Processing**: Efficient workflow for large collections

## Troubleshooting

### Common Issues

1. **Images Not Loading**: Check image file permissions and formats
2. **Captions Not Saving**: Verify write permissions in dataset directory
3. **Navigation Issues**: Ensure dataset contains matching image/caption pairs
4. **Performance Problems**: Consider dataset size and available memory

### Error Handling

- **Missing Files**: Graceful handling of missing caption files
- **Permission Errors**: Clear error messages for file access issues
- **Format Errors**: Support for various image formats with fallbacks
- **Large Files**: Efficient handling of high-resolution images

## Limitations

- Caption files must have matching names with images
- Text-based captions only (no rich formatting)
- Single caption per image
- Requires read/write access to dataset directory
- Memory usage scales with image size
