#!/usr/bin/env python3

import gi
import os
import signal
import subprocess
import psutil
import threading
import sys
from typing import Optional

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Gtk, Adw, GLib, GObject, Gdk, Gio, Pango
from picker_window import PickerWindow, PickerItem

APP_ID = "net.knoopx.process-manager"


class ProcessItem(PickerItem):
    """Represents a running process."""
    __gtype_name__ = "ProcessItem"

    pid = GObject.Property(type=int, default=0)
    name = GObject.Property(type=str, default="")
    cmdline = GObject.Property(type=str, default="")
    username = GObject.Property(type=str, default="")
    cpu_percent = GObject.Property(type=float, default=0.0)
    memory_percent = GObject.Property(type=float, default=0.0)
    memory_rss = GObject.Property(type=int, default=0)
    status = GObject.Property(type=str, default="")
    create_time = GObject.Property(type=float, default=0.0)

    def __init__(self, process):
        super().__init__()
        try:
            # Get process info
            self.pid = process.pid
            self.name = process.name()

            # Get command line, handle permission errors
            try:
                cmdline = process.cmdline()
                self.cmdline = ' '.join(cmdline) if cmdline else self.name
            except (psutil.AccessDenied, psutil.NoSuchProcess):
                self.cmdline = self.name

            # Get username, handle permission errors
            try:
                self.username = process.username()
            except (psutil.AccessDenied, psutil.NoSuchProcess):
                self.username = "unknown"

            # Get CPU and memory usage
            try:
                self.cpu_percent = process.cpu_percent()
                memory_info = process.memory_info()
                self.memory_rss = memory_info.rss
                self.memory_percent = process.memory_percent()
            except (psutil.AccessDenied, psutil.NoSuchProcess):
                self.cpu_percent = 0.0
                self.memory_rss = 0
                self.memory_percent = 0.0

            # Get status and create time
            try:
                self.status = process.status()
                self.create_time = process.create_time()
            except (psutil.AccessDenied, psutil.NoSuchProcess):
                self.status = "unknown"
                self.create_time = 0.0

        except psutil.NoSuchProcess:
            # Process disappeared while we were getting info
            self.pid = 0
            self.name = "Process not found"
            self.cmdline = ""
            self.username = ""
            self.cpu_percent = 0.0
            self.memory_percent = 0.0
            self.memory_rss = 0
            self.status = "gone"
            self.create_time = 0.0

    def get_memory_mb(self):
        """Get memory usage in MB."""
        return self.memory_rss / (1024 * 1024)

    def __eq__(self, other):
        """Compare processes by PID."""
        if not isinstance(other, ProcessItem):
            return False
        return self.pid == other.pid

    def __hash__(self):
        """Hash by PID for use in sets."""
        return hash(self.pid)


class ProcessManagerWindow(PickerWindow):
    def __init__(self, **kwargs):
        # Initialize instance variables before calling super()
        self._current_processes = []
        self._filtered_processes = []
        self._refresh_thread = None
        self._should_refresh = True

        super().__init__(
            title="Process Manager",
            search_placeholder="Search processes by name, PID, or command...",
            window_size=(800, 600),
            search_delay_ms=200,
            **kwargs
        )

        # Start background refresh after initialization
        self._start_refresh_timer()

    # Required abstract method implementations
    def get_item_type(self):
        return ProcessItem

    def use_list_view(self):
        return True  # Use modern ListView approach

    def load_initial_data(self):
        """Load processes on startup."""
        self._refresh_processes()

    def on_search_changed(self, query):
        """Filter processes based on search query."""
        if not query.strip():
            self.on_search_cleared()
            return

        # Filter processes by query (case-insensitive)
        query_lower = query.lower()

        filtered = []
        for process in self._current_processes:
            # Search in name, PID, command line, and username
            if (query_lower in process.name.lower() or
                query_lower in str(process.pid) or
                query_lower in process.cmdline.lower() or
                query_lower in process.username.lower()):
                filtered.append(process)

        self._filtered_processes = filtered
        self._update_ui()

    def on_search_cleared(self):
        """Show all processes when search is cleared."""
        self._filtered_processes = self._current_processes[:]
        self._update_ui()

    def on_item_activated(self, item):
        """Show process details when activated."""
        if not item or item.pid == 0:
            return

        # Show a dialog with process details
        dialog = Adw.MessageDialog.new(
            self,
            f"Process Details: {item.name} (PID: {item.pid})"
        )

        details = f"""
<b>Name:</b> {GLib.markup_escape_text(item.name)}
<b>PID:</b> {item.pid}
<b>User:</b> {GLib.markup_escape_text(item.username)}
<b>Status:</b> {GLib.markup_escape_text(item.status)}
<b>CPU:</b> {item.cpu_percent:.1f}%
<b>Memory:</b> {item.get_memory_mb():.1f} MB ({item.memory_percent:.1f}%)
<b>Command:</b> {GLib.markup_escape_text(item.cmdline if item.cmdline else item.name)}
"""

        dialog.set_body_use_markup(True)
        dialog.set_body(details.strip())
        dialog.add_response("close", "Close")
        dialog.set_default_response("close")
        dialog.present()

    # ListView-specific methods
    def setup_list_item(self, list_item):
        """Setup the UI for each process item."""
        # Main horizontal box
        main_box = Gtk.Box(
            orientation=Gtk.Orientation.HORIZONTAL,
            spacing=12,
            margin_top=8,
            margin_bottom=8,
            margin_start=12,
            margin_end=12,
        )

        # Left side: process info
        info_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        info_box.set_hexpand(True)

        # Process name and PID
        name_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        name_label = Gtk.Label(halign=Gtk.Align.START, xalign=0)
        name_label.set_ellipsize(Pango.EllipsizeMode.END)
        name_label.add_css_class("heading")

        pid_label = Gtk.Label(halign=Gtk.Align.START, xalign=0)
        pid_label.add_css_class("dim-label")
        pid_label.add_css_class("caption")

        name_box.append(name_label)
        name_box.append(pid_label)

        # Command line
        cmd_label = Gtk.Label(halign=Gtk.Align.START, xalign=0)
        cmd_label.set_ellipsize(Pango.EllipsizeMode.END)
        cmd_label.add_css_class("caption")
        cmd_label.set_opacity(0.7)

        # User and status info
        status_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        user_label = Gtk.Label(halign=Gtk.Align.START, xalign=0)
        user_label.add_css_class("caption")
        user_label.set_opacity(0.7)

        status_label = Gtk.Label(halign=Gtk.Align.START, xalign=0)
        status_label.add_css_class("caption")
        status_label.set_opacity(0.7)

        status_box.append(user_label)
        status_box.append(status_label)

        info_box.append(name_box)
        info_box.append(cmd_label)
        info_box.append(status_box)

        # Right side: resource usage
        resource_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        resource_box.set_valign(Gtk.Align.CENTER)

        cpu_label = Gtk.Label(halign=Gtk.Align.END, xalign=1)
        cpu_label.add_css_class("caption")
        cpu_label.set_width_chars(8)

        mem_label = Gtk.Label(halign=Gtk.Align.END, xalign=1)
        mem_label.add_css_class("caption")
        mem_label.set_width_chars(8)

        resource_box.append(cpu_label)
        resource_box.append(mem_label)

        main_box.append(info_box)
        main_box.append(resource_box)

        list_item.set_child(main_box)

    def bind_list_item(self, list_item, item):
        """Bind process data to the list item."""
        main_box = list_item.get_child()
        info_box = main_box.get_first_child()
        resource_box = main_box.get_last_child()

        # Get labels from info box
        name_box = info_box.get_first_child()
        cmd_label = name_box.get_next_sibling()
        status_box = cmd_label.get_next_sibling()

        name_label = name_box.get_first_child()
        pid_label = name_label.get_next_sibling()

        user_label = status_box.get_first_child()
        status_label = user_label.get_next_sibling()

        # Get resource labels
        cpu_label = resource_box.get_first_child()
        mem_label = cpu_label.get_next_sibling()

        # Set process information
        name_label.set_text(item.name)
        pid_label.set_text(f"PID {item.pid}")

        cmd_text = item.cmdline if item.cmdline and item.cmdline != item.name else ""
        cmd_label.set_text(cmd_text)
        cmd_label.set_visible(bool(cmd_text))

        user_label.set_text(f"User: {item.username}")
        status_label.set_text(f"Status: {item.status}")

        # Set resource usage
        cpu_label.set_text(f"CPU: {item.cpu_percent:.1f}%")
        mem_label.set_text(f"RAM: {item.get_memory_mb():.0f}MB")

    # Optional overrides
    def get_empty_icon(self):
        return "system-monitor-symbolic"

    def get_loading_icon(self):
        return "view-refresh-symbolic"

    def get_empty_title(self):
        return "No Processes Found"

    def get_empty_description(self):
        return "Use the search bar to filter processes."

    # Context menu support
    def get_context_menu_actions(self) -> dict:
        """Return actions for process context menu."""
        return {
            "kill_process": "on_kill_process_action",
            "terminate_process": "on_terminate_process_action",
            "show_details": "on_show_details_action",
            "copy_pid": "on_copy_pid_action",
            "copy_command": "on_copy_command_action"
        }

    def get_context_menu_model(self, item) -> Optional[Gio.Menu]:
        """Return context menu model for processes."""
        if not item or item.pid == 0:
            return None

        menu_model = Gio.Menu.new()

        # Check if we can kill this process (not our own process)
        current_pid = os.getpid()
        if item.pid != current_pid:
            menu_model.append("Terminate Process (SIGTERM)", "context.terminate_process")
            menu_model.append("Kill Process (SIGKILL)", "context.kill_process")
            menu_model.append("", None)  # separator

        menu_model.append("Show Details", "context.show_details")
        menu_model.append("", None)  # separator
        menu_model.append("Copy PID", "context.copy_pid")
        menu_model.append("Copy Command", "context.copy_command")

        return menu_model

    def on_kill_process_action(self, action, param):
        """Kill process with SIGKILL."""
        selected_item = self.get_selected_item()
        if not selected_item or selected_item.pid == 0:
            return

        self._confirm_and_kill_process(selected_item, signal.SIGKILL, "KILL")

    def on_terminate_process_action(self, action, param):
        """Terminate process with SIGTERM."""
        selected_item = self.get_selected_item()
        if not selected_item or selected_item.pid == 0:
            return

        self._confirm_and_kill_process(selected_item, signal.SIGTERM, "TERM")

    def on_show_details_action(self, action, param):
        """Show process details."""
        selected_item = self.get_selected_item()
        if selected_item:
            self.on_item_activated(selected_item)

    def on_copy_pid_action(self, action, param):
        """Copy process PID to clipboard."""
        selected_item = self.get_selected_item()
        if selected_item:
            clipboard = self.get_clipboard()
            clipboard.set_text(str(selected_item.pid))

    def on_copy_command_action(self, action, param):
        """Copy process command to clipboard."""
        selected_item = self.get_selected_item()
        if selected_item:
            clipboard = self.get_clipboard()
            clipboard.set_text(selected_item.cmdline if selected_item.cmdline else selected_item.name)

    def _confirm_and_kill_process(self, process_item, sig, signal_name):
        """Show confirmation dialog and kill process."""
        # Don't kill our own process
        if process_item.pid == os.getpid():
            return

        dialog = Adw.MessageDialog.new(
            self,
            f"Confirm Process {signal_name}"
        )

        dialog.set_body(
            f"Are you sure you want to send {signal_name} signal to process "
            f"'{process_item.name}' (PID: {process_item.pid})?\n\n"
            f"This action cannot be undone."
        )

        dialog.add_response("cancel", "Cancel")
        dialog.add_response("confirm", f"Send {signal_name}")
        dialog.set_response_appearance("confirm", Adw.ResponseAppearance.DESTRUCTIVE)
        dialog.set_default_response("cancel")

        dialog.connect("response", self._on_kill_dialog_response, process_item, sig, signal_name)
        dialog.present()

    def _on_kill_dialog_response(self, dialog, response, process_item, sig, signal_name):
        """Handle kill dialog response."""
        if response == "confirm":
            try:
                os.kill(process_item.pid, sig)

                # Show success toast
                toast = Adw.Toast.new(f"Sent {signal_name} signal to PID {process_item.pid}")
                toast.set_timeout(3)

                # Create a toast overlay if we don't have one
                if not hasattr(self, '_toast_overlay'):
                    self._toast_overlay = Adw.ToastOverlay()
                    # We'd need to restructure the UI to add this properly
                    # For now, just print the message
                    print(f"Sent {signal_name} signal to PID {process_item.pid}")

                # Refresh process list after a short delay
                GLib.timeout_add(500, self._refresh_processes)

            except (ProcessLookupError, PermissionError) as e:
                # Show error dialog
                error_dialog = Adw.MessageDialog.new(
                    self,
                    "Failed to Kill Process"
                )
                error_dialog.set_body(f"Could not send {signal_name} signal to process: {str(e)}")
                error_dialog.add_response("close", "Close")
                error_dialog.present()

    def _refresh_processes(self):
        """Refresh the process list."""
        if not self._should_refresh:
            return GLib.SOURCE_REMOVE

        def get_processes():
            """Get processes in background thread."""
            try:
                processes = []
                for proc in psutil.process_iter(['pid', 'name', 'username', 'status', 'create_time']):
                    try:
                        # Create ProcessItem from psutil.Process
                        process_item = ProcessItem(proc)
                        if process_item.pid > 0:  # Only add valid processes
                            processes.append(process_item)
                    except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                        # Skip processes we can't access or that disappeared
                        continue

                # Sort by name only to prevent constant reshuffling
                processes.sort(key=lambda p: p.name.lower())

                # Update UI in main thread
                GLib.idle_add(self._update_process_list, processes)

            except Exception as e:
                print(f"Error refreshing processes: {e}")

        if self._refresh_thread and self._refresh_thread.is_alive():
            return GLib.SOURCE_CONTINUE

        self._refresh_thread = threading.Thread(target=get_processes, daemon=True)
        self._refresh_thread.start()

        return GLib.SOURCE_CONTINUE

    def _update_process_list(self, processes):
        """Update the process list in the main thread."""
        self._current_processes = processes

        # Apply current search filter
        current_query = self.get_search_text()
        if current_query.strip():
            self.on_search_changed(current_query)
        else:
            self.on_search_cleared()

        return GLib.SOURCE_REMOVE

    def _update_ui(self):
        """Update the UI with current filtered processes, preserving existing items and selection when possible."""
        if not self._filtered_processes:
            self.remove_all_items()
            self._show_empty("No Processes Found", "No processes match your search criteria.")
            return

        # Remember the currently selected process PID and position
        selected_pid = None
        selected_position = None
        if self.use_list_view():
            selected_position = self._selection_model.get_selected()
            if selected_position != Gtk.INVALID_LIST_POSITION:
                selected_item = self._item_store.get_item(selected_position)
                if selected_item:
                    selected_pid = selected_item.pid

        # Get current items from the store
        current_items = []
        for i in range(self._item_store.get_n_items()):
            current_items.append(self._item_store.get_item(i))

        # Create sets for efficient comparison
        current_pids = {item.pid for item in current_items}
        new_pids = {process.pid for process in self._filtered_processes}

        # Find processes to add and remove
        pids_to_add = new_pids - current_pids
        pids_to_remove = current_pids - new_pids

        # If we have significant changes (many adds/removes), rebuild the entire list
        # This helps maintain proper sorting order
        if len(pids_to_add) > 10 or len(pids_to_remove) > 10:
            self.remove_all_items()
            for process in self._filtered_processes:
                self.add_item(process)
        else:
            # For small changes, do incremental updates

            # Remove processes that are no longer running or don't match filter
            # Remove from end to beginning to maintain indices
            for i in reversed(range(len(current_items))):
                item = current_items[i]
                if item.pid in pids_to_remove:
                    self._item_store.remove(i)

            # Add new processes in alphabetical order
            processes_to_add = []
            for process in self._filtered_processes:
                if process.pid in pids_to_add:
                    processes_to_add.append(process)

            # Sort the new processes by name
            processes_to_add.sort(key=lambda p: p.name.lower())

            # Add them to the store
            for process in processes_to_add:
                self.add_item(process)

            # Update existing processes in place
            # We need to update the items that are still in the list
            for i in range(self._item_store.get_n_items()):
                current_item = self._item_store.get_item(i)
                # Find the corresponding new process data
                for new_process in self._filtered_processes:
                    if new_process.pid == current_item.pid:
                        # Update the properties that might have changed
                        current_item.cpu_percent = new_process.cpu_percent
                        current_item.memory_rss = new_process.memory_rss
                        current_item.memory_percent = new_process.memory_percent
                        current_item.status = new_process.status
                        # Notify the UI that the item has changed
                        self._item_store.items_changed(i, 1, 1)
                        break

        self._show_results()

        # Restore selection if the selected process is still in the list
        # Do this immediately instead of using idle_add for better reliability
        if selected_pid is not None:
            self._restore_selection(selected_pid)

    def _restore_selection(self, selected_pid):
        """Restore selection to the process with the given PID."""
        for i in range(self._item_store.get_n_items()):
            item = self._item_store.get_item(i)
            if item.pid == selected_pid:
                self._selection_model.set_selected(i)
                return True
        return False

    def _start_refresh_timer(self):
        """Start the process refresh timer."""
        # Refresh every 2 seconds
        GLib.timeout_add(2000, self._refresh_processes)

    def on_close_request(self):
        """Handle window close request."""
        self._should_refresh = False
        return False  # Allow close

    def on_additional_key_pressed(self, keyval, keycode, state) -> bool:
        """Handle additional keyboard shortcuts."""
        # Handle Ctrl+O for context menu
        if (keyval == Gdk.KEY_o and
            state & Gdk.ModifierType.CONTROL_MASK and
            not state & Gdk.ModifierType.SHIFT_MASK and
            not state & Gdk.ModifierType.ALT_MASK):
            selected_item = self.get_selected_item()
            if selected_item:
                menu_model = self.get_context_menu_model(selected_item)
                if menu_model:
                    self.show_context_menu()
            return True
        return False


class ProcessManagerApplication(Adw.Application):
    def __init__(self):
        super().__init__(
            application_id=APP_ID,
            flags=Gio.ApplicationFlags.FLAGS_NONE,
        )

    def do_activate(self):
        win = self.props.active_window
        if not win:
            win = ProcessManagerWindow(application=self)
        win.present()

    def do_startup(self):
        Adw.Application.do_startup(self)


def main():
    app = ProcessManagerApplication()
    return app.run(sys.argv)


if __name__ == "__main__":
    main()
