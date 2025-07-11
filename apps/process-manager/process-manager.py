#!/usr/bin/env python3
import gi
import os
import signal
import psutil
import threading
import sys
from typing import Optional

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw, GLib, GObject, Gio
from picker_window import PickerWindow, PickerItem

APP_ID = "net.knoopx.process-manager"


class ProcessListItem(Gtk.Box):
    def __init__(self):
        import gi.repository.Pango as Pango
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=0, margin_top=0, margin_bottom=0, margin_start=0, margin_end=0)

        self.main_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12, margin_top=8, margin_bottom=8, margin_start=12, margin_end=12)
        self.info_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        self.info_box.set_hexpand(True)
        self.name_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        self.name_label = Gtk.Label(halign=Gtk.Align.START, xalign=0)
        self.name_label.set_ellipsize(Pango.EllipsizeMode.END)
        self.name_label.add_css_class('heading')
        self.pid_label = Gtk.Label(halign=Gtk.Align.START, xalign=0)
        self.pid_label.add_css_class('dim-label')
        self.pid_label.add_css_class('caption')
        self.name_box.append(self.name_label)
        self.name_box.append(self.pid_label)
        self.cmd_label = Gtk.Label(halign=Gtk.Align.START, xalign=0)
        self.cmd_label.set_ellipsize(Pango.EllipsizeMode.START)
        self.cmd_label.add_css_class('caption')
        self.cmd_label.set_opacity(0.7)
        self.status_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        self.user_label = Gtk.Label(halign=Gtk.Align.START, xalign=0)
        self.user_label.add_css_class('caption')
        self.user_label.set_opacity(0.7)
        self.status_label = Gtk.Label(halign=Gtk.Align.START, xalign=0)
        self.status_label.add_css_class('caption')
        self.status_label.set_opacity(0.7)
        self.status_box.append(self.user_label)
        self.status_box.append(self.status_label)
        self.info_box.append(self.name_box)
        self.info_box.append(self.cmd_label)
        self.info_box.append(self.status_box)
        self.resource_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        self.resource_box.set_valign(Gtk.Align.CENTER)
        self.cpu_label = Gtk.Label(halign=Gtk.Align.END, xalign=1)
        self.cpu_label.add_css_class('caption')
        self.cpu_label.set_width_chars(8)
        self.mem_label = Gtk.Label(halign=Gtk.Align.END, xalign=1)
        self.mem_label.add_css_class('caption')
        self.mem_label.set_width_chars(8)
        self.resource_box.append(self.cpu_label)
        self.resource_box.append(self.mem_label)
        self.main_box.append(self.info_box)
        self.main_box.append(self.resource_box)
        self.append(self.main_box)


class ProcessItem(PickerItem):
    __gtype_name__ = "ProcessItem"
    pid = GObject.Property(type=int, default=0)
    name = GObject.Property(type=str, default="")
    cmdline = GObject.Property(type=str, default="")
    username = GObject.Property(type=str, default="")
    cpu_percent = GObject.Property(type=float, default=0.0)
    memory_percent = GObject.Property(type=float, default=0.0)
    memory_rss = GObject.Property(type=GObject.TYPE_INT64, default=0)
    status = GObject.Property(type=str, default="")
    create_time = GObject.Property(type=float, default=0.0)

    def __init__(self, process):
        super().__init__()
        try:
            self.pid = process.pid
            self.name = process.name()
            try:
                cmdline = process.cmdline()
                self.cmdline = " ".join(cmdline) if cmdline else self.name
            except (psutil.AccessDenied, psutil.NoSuchProcess):
                self.cmdline = self.name
            try:
                self.username = process.username()
            except (psutil.AccessDenied, psutil.NoSuchProcess):
                self.username = "unknown"
            try:
                self.cpu_percent = process.cpu_percent()
                memory_info = process.memory_info()
                self.memory_rss = memory_info.rss
                self.memory_percent = process.memory_percent()
            except (psutil.AccessDenied, psutil.NoSuchProcess):
                self.cpu_percent = 0.0
                self.memory_rss = 0
                self.memory_percent = 0.0
            try:
                self.status = process.status()
                self.create_time = process.create_time()
            except (psutil.AccessDenied, psutil.NoSuchProcess):
                self.status = "unknown"
                self.create_time = 0.0
        except psutil.NoSuchProcess:
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
        return self.memory_rss / (1024 * 1024)

    def __eq__(self, other):
        if not isinstance(other, ProcessItem):
            return False
        return self.pid == other.pid

    def __hash__(self):
        return hash(self.pid)


class ProcessManagerWindow(PickerWindow):

    def __init__(self, **kwargs):
        self._current_processes = []
        self._filtered_processes = []
        self._refresh_thread = None
        self._should_refresh = True
        super().__init__(
            title="Process Manager",
            search_placeholder="Search processes by name, PID, or command...",
            **kwargs,
        )
        self._start_refresh_timer()

    def get_item_type(self):
        return ProcessItem

    def load_initial_data(self):
        self._refresh_processes()

    def on_search_changed(self, query):
        if not query.strip():
            self.on_search_cleared()
            return
        query_lower = query.lower()
        filtered = []
        for process in self._current_processes:
            if (
                query_lower in process.name.lower()
                or query_lower in str(process.pid)
                or query_lower in process.cmdline.lower()
                or (query_lower in process.username.lower())
            ):
                filtered.append(process)
        self._filtered_processes = filtered
        self._update_ui()

    def on_search_cleared(self):
        self._filtered_processes = self._current_processes[:]
        self._update_ui()

    def on_item_activated(self, item):
        if not item or item.pid == 0:
            return
        dialog = Adw.MessageDialog.new(
            self, f"Process Details: {item.name} (PID: {item.pid})"
        )
        details = f"\n<b>Name:</b> {GLib.markup_escape_text(item.name)}\n<b>PID:</b> {item.pid}\n<b>User:</b> {GLib.markup_escape_text(item.username)}\n<b>Status:</b> {GLib.markup_escape_text(item.status)}\n<b>CPU:</b> {item.cpu_percent:.1f}%\n<b>Memory:</b> {item.get_memory_mb():.1f} MB ({item.memory_percent:.1f}%)\n<b>Command:</b> {GLib.markup_escape_text(item.cmdline if item.cmdline else item.name)}\n"
        dialog.set_body_use_markup(True)
        dialog.set_body(details.strip())
        dialog.add_response("close", "Close")
        dialog.set_default_response("close")
        dialog.present()

    def setup_list_item(self, list_item):
        widget = ProcessListItem()
        list_item.set_child(widget)

    def bind_list_item(self, list_item, item):
        widget = list_item.get_child()
        if isinstance(widget, ProcessListItem):
            widget.name_label.set_text(item.name)
            widget.pid_label.set_text(str(item.pid))
            cmd_text = (
                item.cmdline if item.cmdline and item.cmdline != item.name else ""
            )
            widget.cmd_label.set_text(cmd_text)
            widget.cmd_label.set_visible(bool(cmd_text))
            widget.user_label.set_text(item.username)
            widget.status_label.set_text(item.status)
            widget.cpu_label.set_text(f"{item.cpu_percent:.1f}%")
            widget.mem_label.set_text(f"{item.get_memory_mb():.0f}MB")

    def get_empty_icon(self):
        return "find-location-symbolic"

    def get_loading_icon(self):
        return "view-refresh-symbolic"

    def get_empty_title(self):
        return "No Processes Found"

    def get_empty_description(self):
        return "Use the search bar to filter processes."

    def get_context_menu_model(self, item) -> Optional[Gio.Menu]:
        if not item or item.pid == 0:
            return None
        menu_model = Gio.Menu.new()
        menu_model.append("Terminate Process", "context.on_terminate_process_action")
        menu_model.append("Kill Process", "context.on_kill_process_action")
        menu_model.append("Copy PID", "context.on_copy_pid_action")
        menu_model.append("Copy Command", "context.on_copy_command_action")
        return menu_model

    def on_kill_process_action(self, action, param):
        selected_item = self.get_selected_item()
        if not selected_item or selected_item.pid == 0:
            return
        self._kill_process(selected_item, signal.SIGKILL)

    def on_terminate_process_action(self, action, param):
        selected_item = self.get_selected_item()
        if not selected_item or selected_item.pid == 0:
            return
        self._kill_process(selected_item, signal.SIGTERM)

    def on_show_details_action(self, action, param):
        selected_item = self.get_selected_item()
        if selected_item:
            self.on_item_activated(selected_item)

    def on_copy_pid_action(self, action, param):
        selected_item = self.get_selected_item()
        if selected_item:
            clipboard = self.get_clipboard()
            clipboard.set(str(selected_item.pid))

    def on_copy_command_action(self, action, param):
        selected_item = self.get_selected_item()
        if selected_item:
            clipboard = self.get_clipboard()
            clipboard.set(
                selected_item.cmdline if selected_item.cmdline else selected_item.name
            )

    def _kill_process(self, process_item, sig):
        os.kill(process_item.pid, sig)

    def _refresh_processes(self):
        if not self._should_refresh:
            return GLib.SOURCE_REMOVE

        def get_processes():
            try:
                processes = []
                for proc in psutil.process_iter(
                    ["pid", "name", "username", "status", "create_time"]
                ):
                    try:
                        process_item = ProcessItem(proc)
                        if process_item.pid > 0:
                            processes.append(process_item)
                    except (
                        psutil.NoSuchProcess,
                        psutil.AccessDenied,
                        psutil.ZombieProcess,
                    ):
                        continue
                processes.sort(key=lambda p: p.name.lower())
                GLib.idle_add(self._update_process_list, processes)
            except Exception as e:
                print(f"Error refreshing processes: {e}")

        if self._refresh_thread and self._refresh_thread.is_alive():
            return GLib.SOURCE_CONTINUE
        self._refresh_thread = threading.Thread(target=get_processes, daemon=True)
        self._refresh_thread.start()
        return GLib.SOURCE_CONTINUE

    def _update_process_list(self, processes):
        self._current_processes = processes
        current_query = self.get_search_text()
        if current_query.strip():
            self.on_search_changed(current_query)
        else:
            self.on_search_cleared()
        return GLib.SOURCE_REMOVE

    def _update_ui(self):
        if not self._filtered_processes:
            self.remove_all_items()
            self._show_empty(
                "No Processes Found", "No processes match your search criteria."
            )
            return
        selected_pid = None
        selected_position = None
        selected_position = self._selection_model.get_selected()
        if selected_position != Gtk.INVALID_LIST_POSITION:
            selected_item = self._item_store.get_item(selected_position)
            if selected_item:
                selected_pid = selected_item.pid
        current_items = []
        for i in range(self._item_store.get_n_items()):
            current_items.append(self._item_store.get_item(i))
        current_pids = {item.pid for item in current_items}
        new_pids = {process.pid for process in self._filtered_processes}
        pids_to_add = new_pids - current_pids
        pids_to_remove = current_pids - new_pids
        if len(pids_to_add) > 10 or len(pids_to_remove) > 10:
            self.remove_all_items()
            for process in self._filtered_processes:
                self.add_item(process)
        else:
            for i in reversed(range(len(current_items))):
                item = current_items[i]
                if item.pid in pids_to_remove:
                    self._item_store.remove(i)
            processes_to_add = []
            for process in self._filtered_processes:
                if process.pid in pids_to_add:
                    processes_to_add.append(process)
            processes_to_add.sort(key=lambda p: p.name.lower())
            for process in processes_to_add:
                self.add_item(process)
            for i in range(self._item_store.get_n_items()):
                current_item = self._item_store.get_item(i)
                if current_item is not None:
                    for new_process in self._filtered_processes:
                        if new_process.pid == current_item.pid:
                            current_item.cpu_percent = new_process.cpu_percent
                            current_item.memory_rss = new_process.memory_rss
                            current_item.memory_percent = new_process.memory_percent
                            current_item.status = new_process.status
                            self._item_store.items_changed(i, 1, 1)
                            break
        self._show_results()
        if selected_pid is not None:
            self._restore_selection(selected_pid)

    def _restore_selection(self, selected_pid):
        for i in range(self._item_store.get_n_items()):
            item = self._item_store.get_item(i)
            if item is not None and item.pid == selected_pid:
                self._selection_model.set_selected(i)
                return True
        return False

    def _start_refresh_timer(self):
        GLib.timeout_add(2000, self._refresh_processes)

    def on_close_request(self):
        self._should_refresh = False
        return False


class ProcessManagerApplication(Adw.Application):

    def __init__(self):
        super().__init__(application_id=APP_ID, flags=Gio.ApplicationFlags.FLAGS_NONE)

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
