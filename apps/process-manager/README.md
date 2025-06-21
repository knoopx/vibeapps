# Process Manager

## Overview

A powerful system process manager with advanced filtering, process control, and real-time monitoring capabilities. View detailed process information, manage running processes, and monitor system resource usage.

## Features

- **Real-time Monitoring**: Live process information with automatic updates
- **Advanced Search**: Filter processes by name, command, user, or PID
- **Process Control**: Terminate, kill, or send signals to processes
- **Resource Monitoring**: CPU and memory usage tracking
- **User Filtering**: Filter processes by username or current user
- **Detailed Information**: Comprehensive process metadata
- **Keyboard Navigation**: Efficient keyboard-driven interface
- **Safety Features**: Confirmation dialogs for destructive actions
- **Permission Handling**: Graceful handling of restricted processes

## Usage

### Basic Operations

#### Viewing Processes
1. **Launch**: Start the process manager
2. **Browse**: Scroll through the list of running processes
3. **Search**: Type to filter processes by various criteria
4. **Select**: Click or use arrow keys to select processes

#### Process Control
1. **Select Process**: Choose a process from the list
2. **Context Menu**: Right-click or use keyboard shortcuts
3. **Choose Action**: Terminate, kill, or send custom signals
4. **Confirm**: Confirm destructive actions when prompted

#### Search and Filtering
1. **Search Bar**: Type to filter processes instantly
2. **Multiple Criteria**: Search by name, command, user, or PID
3. **Real-time Filter**: Results update as you type
4. **Clear Filter**: Clear search to show all processes

### Keyboard Shortcuts

#### Navigation
- **↑/↓**: Navigate through process list
- **Page Up/Down**: Quick navigation through long lists
- **Home/End**: Jump to first/last process
- **Enter**: Select/focus on process

#### Process Control
- **Delete**: Terminate selected process (SIGTERM)
- **Shift+Delete**: Force kill selected process (SIGKILL)
- **Ctrl+K**: Send custom signal to process
- **F5**: Refresh process list

#### Interface
- **Ctrl+F**: Focus search bar
- **Escape**: Clear search and return to full list
- **Ctrl+Q**: Quit application

## Features in Detail

### Process Information

#### Core Details
- **PID**: Process identifier
- **Name**: Process executable name
- **Command Line**: Full command with arguments
- **User**: Process owner username
- **Status**: Current process status (running, sleeping, etc.)
- **CPU Usage**: Current CPU utilization percentage
- **Memory Usage**: RAM usage (RSS) and percentage
- **Creation Time**: When the process was started

#### Advanced Metadata
- **Parent Process**: Parent PID and relationships
- **Process Group**: Process group information
- **Session ID**: Session identifier
- **Thread Count**: Number of threads
- **File Descriptors**: Open file descriptor count
- **Working Directory**: Current working directory

### Process Control

#### Signal Management
- **SIGTERM (15)**: Graceful termination request
- **SIGKILL (9)**: Force immediate termination
- **SIGHUP (1)**: Hangup signal (reload configuration)
- **SIGINT (2)**: Interrupt signal (Ctrl+C equivalent)
- **SIGSTOP (19)**: Pause process execution
- **SIGCONT (18)**: Resume paused process
- **Custom Signals**: Send any signal by number

#### Safety Features
- **Confirmation Dialogs**: Confirm before terminating processes
- **Permission Checking**: Handles insufficient permissions gracefully
- **System Process Protection**: Warnings for critical system processes
- **Error Handling**: Clear error messages for failed operations

### Search and Filtering

#### Search Criteria
- **Process Name**: Filter by executable name
- **Command Line**: Search within full command arguments
- **Username**: Filter by process owner
- **PID**: Search by specific process ID
- **Combined Search**: Multiple criteria simultaneously

#### Search Features
- **Real-time Results**: Updates as you type
- **Case Insensitive**: Ignores case differences
- **Partial Matching**: Finds partial matches anywhere in fields
- **Regular Expressions**: Advanced pattern matching support

### Performance Monitoring

#### Resource Tracking
- **CPU Utilization**: Per-process CPU usage percentage
- **Memory Consumption**: Physical memory (RSS) usage
- **Memory Percentage**: Memory usage as percentage of total
- **Update Frequency**: Real-time updates with configurable intervals

#### System Overview
- **Total Processes**: Count of running processes
- **Resource Summary**: Aggregated system resource usage
- **Performance Impact**: Monitor manager's own resource usage
- **Efficiency**: Optimized for minimal system impact

## Technical Details

### Architecture

- **Frontend**: GTK4 with Adwaita design system
- **Backend**: Python psutil for process information
- **Threading**: Background process monitoring
- **Caching**: Efficient process list caching

### Process Management

#### Data Collection
- **psutil Integration**: Comprehensive process information
- **Permission Handling**: Graceful degradation for restricted processes
- **Error Recovery**: Handles process disappearance during enumeration
- **Performance Optimization**: Efficient data collection strategies

#### Signal Handling
```python
# Signal sending with error handling
try:
    process.send_signal(signal_number)
except psutil.NoSuchProcess:
    # Process already terminated
except psutil.AccessDenied:
    # Insufficient permissions
```

### Performance

#### Optimization Strategies
- **Lazy Loading**: Process details loaded on demand
- **Efficient Updates**: Only update visible process information
- **Memory Management**: Minimal memory footprint
- **Background Threading**: Non-blocking UI updates

#### Scalability
- **Large Process Counts**: Handles systems with thousands of processes
- **Real-time Updates**: Maintains responsiveness during updates
- **Resource Monitoring**: Monitors own performance impact
- **Adaptive Refresh**: Adjusts update frequency based on system load

## Process Information Details

### Status Codes

- **Running**: Currently executing
- **Sleeping**: Waiting for resources or events
- **Disk Sleep**: Waiting for I/O operations
- **Stopped**: Suspended execution
- **Zombie**: Terminated but not cleaned up
- **Dead**: Process has terminated

### Memory Types

- **RSS (Resident Set Size)**: Physical memory currently used
- **VMS (Virtual Memory Size)**: Total virtual memory used
- **Shared Memory**: Memory shared with other processes
- **Text Segment**: Memory used for executable code
- **Data Segment**: Memory used for program data

### CPU Metrics

- **CPU Percent**: Percentage of CPU time used
- **CPU Times**: User and system CPU time consumed
- **CPU Affinity**: Which CPU cores the process can use
- **Priority**: Process scheduling priority

## Use Cases

### System Administration

- **Performance Monitoring**: Track resource-intensive processes
- **Troubleshooting**: Identify problematic processes
- **Resource Management**: Manage system resources effectively
- **Security Monitoring**: Monitor for suspicious processes

### Development

- **Process Debugging**: Monitor development processes
- **Resource Profiling**: Profile application resource usage
- **Service Management**: Manage development services
- **Build Monitoring**: Track build processes and resource usage

### General Use

- **System Cleanup**: Identify and terminate unnecessary processes
- **Performance Optimization**: Find resource bottlenecks
- **Process Investigation**: Research unknown processes
- **System Learning**: Understand system operation

## Troubleshooting

### Common Issues

1. **Permission Denied**: Some processes require elevated privileges
2. **Process Disappeared**: Processes may terminate during inspection
3. **High Resource Usage**: Monitor system impact of the manager itself
4. **Slow Updates**: Large process counts may slow refresh

### Error Handling

- **Access Denied**: Clear messages for permission issues
- **Process Not Found**: Handles processes that terminate during operation
- **Signal Failures**: Appropriate error messages for failed signal delivery
- **System Limits**: Graceful handling of system resource limits

### Performance Tips

- **Filter Processes**: Use search to reduce visible process count
- **Refresh Rate**: Balance update frequency with performance
- **Close When Idle**: Close when not actively monitoring
- **Monitor Resources**: Watch the manager's own resource usage

## Limitations

- Requires appropriate permissions to control processes
- Cannot access all process information for privileged processes
- Real-time monitoring depends on system performance
- Signal delivery success depends on process state and permissions
- Limited to processes visible to the current user (unless run as root)
- Cannot manage kernel threads or some system processes
