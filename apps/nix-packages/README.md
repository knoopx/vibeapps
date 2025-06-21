# Nix Package Search

## Overview

A modern graphical interface for searching and exploring Nix packages from the official NixOS package repository. Features real-time search, detailed package information, and integration with the Nix ecosystem.

## Features

- **Real-time Search**: Instant search results as you type
- **Package Details**: Comprehensive information for each package
- **Version Information**: Current package versions and metadata
- **License Information**: Package licensing details
- **Homepage Links**: Direct links to project homepages
- **Copy Package Names**: Easy copying of package names for use in configurations
- **Threaded Search**: Non-blocking search operations
- **Modern Interface**: Clean, responsive GTK4 interface

## Usage

### Basic Search

1. **Launch**: Start the Nix package search application
2. **Search**: Type package names, descriptions, or keywords
3. **Browse**: Navigate through search results
4. **Details**: View package information including versions and licenses
5. **Copy**: Copy package names for use in your Nix configurations

### Search Examples

#### Package Names
```
firefox → Mozilla Firefox browser
git → Git version control system
python3 → Python 3 interpreter
nodejs → Node.js runtime
```

#### Keywords and Descriptions
```
text editor → Various text editing packages
web browser → Browser applications
development → Development tools and libraries
multimedia → Audio/video applications
```

#### Specific Use Cases
```
gcc → GNU Compiler Collection
docker → Container platform
kubernetes → Container orchestration
nginx → Web server
postgresql → Database system
```

## Features in Detail

### Search Capabilities

#### Real-time Results
- **Instant Feedback**: Results appear as you type
- **Progressive Refinement**: Narrow results with additional keywords
- **Fuzzy Matching**: Find packages even with approximate terms
- **Description Search**: Searches both names and descriptions

#### Search API Integration
- **Official Repository**: Searches NixOS official package repository
- **Current Packages**: Always up-to-date package information
- **Comprehensive Coverage**: Includes all available Nix packages
- **Fast Response**: Optimized search backend

### Package Information

#### Core Details
- **Package Name**: Official Nix package identifier
- **Version**: Current version in the repository
- **Description**: Detailed package description
- **Homepage**: Link to project website
- **License**: Package licensing information

#### Additional Metadata
- **Maintainers**: Package maintainer information
- **Platforms**: Supported platforms and architectures
- **Dependencies**: Package dependencies (where available)
- **Build Information**: Build status and details

### User Interface

#### Layout
- **Search Bar**: Prominent search input at the top
- **Results List**: Scrollable list of matching packages
- **Detail Panel**: Selected package information
- **Action Buttons**: Copy and link actions

#### Navigation
- **Keyboard**: Full keyboard navigation support
- **Mouse**: Click and scroll interactions
- **Search Focus**: Quick return to search with Escape
- **Result Selection**: Arrow keys and mouse selection

## Technical Details

### Architecture

- **Frontend**: GTK4 with Adwaita design system
- **Backend**: NixOS search API integration
- **Threading**: Background search operations
- **Caching**: Efficient result caching

### API Integration

#### Search Endpoint
```
https://search.nixos.org/backend/latest-43-nixos-unstable/_search
```

#### Authentication
- Uses authenticated API access for reliable service
- Handles rate limiting gracefully
- Provides fallback behavior for API issues

#### Response Processing
- **JSON Parsing**: Processes search API responses
- **Error Handling**: Graceful handling of API errors
- **Result Formatting**: Converts API data to display format

### Performance

#### Search Optimization
- **Debounced Input**: Reduces unnecessary API calls
- **Background Threading**: Non-blocking search operations
- **Result Caching**: Caches recent search results
- **Progressive Loading**: Loads results incrementally

#### Memory Management
- **Efficient Lists**: GTK ListBox for large result sets
- **Object Cleanup**: Proper cleanup of search results
- **Resource Management**: Minimal memory footprint

## Integration with Nix

### Package Installation

Copy package names from search results for use in:

#### NixOS Configuration
```nix
environment.systemPackages = with pkgs; [
  firefox
  git
  python3
];
```

#### Home Manager
```nix
home.packages = with pkgs; [
  nodejs
  docker
  kubernetes
];
```

#### Nix Shell
```bash
nix-shell -p firefox git python3
```

#### Nix Development Environments
```nix
pkgs.mkShell {
  buildInputs = with pkgs; [
    nodejs
    python3
    postgresql
  ];
}
```

## Use Cases

### Package Discovery

- **Explore Packages**: Browse available software in Nix repository
- **Version Checking**: Verify current package versions
- **License Research**: Check package licensing for compliance
- **Alternative Finding**: Discover alternative packages

### Development Workflow

- **Environment Setup**: Find packages for development environments
- **Dependency Management**: Research package dependencies
- **Tool Discovery**: Find development tools and utilities
- **System Configuration**: Build system package lists

### System Administration

- **Package Planning**: Plan system package installations
- **Update Research**: Check for package updates and changes
- **Compatibility**: Verify package availability and versions
- **Documentation**: Access package homepages and documentation

## Troubleshooting

### Common Issues

1. **No Search Results**: Check internet connection and API availability
2. **Slow Searches**: Network latency may affect search speed
3. **Missing Information**: Some packages may have incomplete metadata
4. **API Errors**: Service may be temporarily unavailable

### Error Handling

- **Network Issues**: Graceful handling of connection problems
- **API Limits**: Respects rate limiting and retry policies
- **Invalid Searches**: Handles malformed queries safely
- **Empty Results**: Clear indication when no packages match

### Performance Tips

- **Specific Terms**: Use specific search terms for better results
- **Wait for Typing**: Let searches complete before typing more
- **Clear Cache**: Restart application if performance degrades
- **Network Speed**: Faster internet improves search responsiveness

## Limitations

- Requires internet connection for search functionality
- Depends on NixOS search API availability
- Search results limited by API response size
- Package installation requires separate Nix commands
- Limited to packages in official NixOS repository
- Does not show local package installations or custom packages
