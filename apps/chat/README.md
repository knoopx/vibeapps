# Chat

## Overview

An AI-powered chat application that provides a conversational interface using OpenAI's GPT models. Features real-time streaming responses with markdown rendering and conversation history management.

## Features

- **Real-time streaming**: Get responses as they're generated
- **Markdown rendering**: Rich text formatting with proper HTML output
- **Conversation history**: Maintains context across multiple exchanges
- **WebKit integration**: Modern web-based interface for rich content display
- **Error handling**: Graceful error management for API issues
- **Threaded processing**: Non-blocking UI with background message processing

## Configuration

### Environment Variables

The application requires the following environment variables:

- **OPENAI_API_KEY**: Your OpenAI API key for authentication
- **OPENAI_API_BASE** (optional): Custom API base URL if using alternative endpoints

### Setup

1. Set your OpenAI API credentials:
   ```bash
   export OPENAI_API_KEY="your-api-key-here"
   export OPENAI_API_BASE="https://api.openai.com/v1"  # Optional
   ```

2. Ensure the `md2html` utility is available for markdown rendering

## Usage

### Starting a Conversation

1. Launch the chat application
2. Type your message in the input field
3. Press Enter or click Send to submit
4. Watch as the AI response streams in real-time

### Features in Detail

#### Markdown Support

The application converts markdown responses to HTML for rich display:
- **Bold** and *italic* text
- Code blocks with syntax highlighting
- Lists and headers
- Links and formatting

#### Conversation Memory

The chat maintains conversation history:
- Previous messages provide context for new responses
- Full conversation thread is preserved during the session
- AI responses build upon earlier context

#### Error Handling

Robust error management for common issues:
- Invalid API keys
- Network connectivity problems
- API rate limiting
- Malformed responses

## Technical Details

### Architecture

- **Frontend**: GTK4 with Adwaita design
- **Backend**: OpenAI Python SDK for API communication
- **Rendering**: WebKit for markdown-to-HTML display
- **Threading**: Async processing for responsive UI

### Components

- **OpenAIStreamer**: Manages API communication and conversation history
- **Markdown Processing**: Converts responses to HTML using md2html utility
- **WebKit View**: Displays formatted responses
- **Message History**: Maintains conversation context

### Dependencies

- `gi` (PyGObject) for GTK interface
- `openai` for API communication
- `webkit` for web content rendering
- `md2html` utility for markdown processing

## Keyboard Shortcuts

- **Enter**: Send message
- **Ctrl+Q**: Quit application
- **Ctrl+N**: New conversation (clears history)

## Troubleshooting

### Common Issues

1. **API Key Error**: Ensure OPENAI_API_KEY is set correctly
2. **Markdown Rendering**: Verify md2html utility is installed and accessible
3. **Connection Issues**: Check internet connectivity and API base URL
4. **Streaming Problems**: Ensure API key has appropriate permissions

### Error Messages

- "OpenAI client not initialized": Check API key configuration
- "Markdown rendering error": Verify md2html installation
- Network errors: Check connectivity and API endpoints

## Limitations

- Requires active internet connection
- Depends on OpenAI API availability
- Conversation history resets when application closes
- Limited to text-based interactions
- Requires valid OpenAI API key with appropriate usage limits
