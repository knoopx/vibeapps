#!/usr/bin/env python3
import sys
import os
import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
gi.require_version("GdkPixbuf", "2.0")
from gi.repository import Gtk, Adw, Gio, GLib, Gdk, GdkPixbuf

import threading
from gi.repository import GObject

@GObject.type_register
class FileItem(GObject.Object):
    __gtype_name__ = "FilePickerFileItem"
    name = GObject.Property(type=str)
    size = GObject.Property(type=str)
    selected = GObject.Property(type=bool, default=False)
    group_id = GObject.Property(type=int, default=0)

    def __init__(self, name, size, group_id=0, selected=False):
        super().__init__()
        self.set_property("name", name)
        self.set_property("size", size)
        self.set_property("group_id", group_id)
        self.set_property("selected", selected)

class SectionHeaderWidget(Gtk.Box):
    def __init__(self):
        super().__init__(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        self.set_hexpand(True)
        self.set_halign(Gtk.Align.FILL)
        self.set_margin_start(12)
        self.set_margin_end(12)
        self.label = Gtk.Label(xalign=0)
        self.label.set_hexpand(True)
        self.label.set_halign(Gtk.Align.START)
        self.append(self.label)

class PickerRowWidget(Gtk.Box):
    def __init__(self):
        super().__init__(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        self.set_hexpand(True)
        self.set_halign(Gtk.Align.FILL)
        self.set_size_request(-1, 36)
        self.set_margin_start(12)
        self.set_margin_end(12)
        self.set_margin_top(4)
        self.set_margin_bottom(4)

        self.thumbnail = Gtk.Image()
        self.thumbnail.set_pixel_size(32)
        self.append(self.thumbnail)

        self.check = Gtk.CheckButton()
        self.append(self.check)

        self.name_label = Gtk.Label(xalign=0)
        self.name_label.set_hexpand(True)
        self.name_label.set_halign(Gtk.Align.START)
        self.append(self.name_label)

        self.size_label = Gtk.Label(xalign=0)
        self.size_label.set_halign(Gtk.Align.START)
        self.append(self.size_label)

        self.set_can_focus(True)
        self.add_css_class("row-clickable")
        gesture = Gtk.GestureClick()
        gesture.connect("pressed", self.on_row_clicked)
        self.add_controller(gesture)

    def on_row_clicked(self, gesture, n_press, x, y):
        alloc = self.check.get_allocation()
        if not (alloc.x <= x <= alloc.x + alloc.width and alloc.y <= y <= alloc.y + alloc.height):
            self.check.set_active(not self.check.get_active())

    def set_file(self, file_path, size_str):
        self.name_label.set_text(file_path)
        self.size_label.set_text(size_str)
        if PickerRowWidget.is_image_file(file_path):
            try:
                pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_size(file_path, 32, 32)
                self.thumbnail.set_from_pixbuf(pixbuf)
            except Exception:
                self.thumbnail.clear()
        else:
            self.thumbnail.clear()

    @staticmethod
    def is_image_file(file_path):
        image_exts = {'.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp', '.tiff'}
        ext = os.path.splitext(file_path)[1].lower()
        return ext in image_exts

    @staticmethod
    def format_size(num_bytes):
        for unit in ['B', 'KB', 'MB', 'GB', 'TB', 'PB']:
            if num_bytes < 1024.0:
                return f"{num_bytes:.1f} {unit}" if unit != 'B' else f"{num_bytes} B"
            num_bytes /= 1024.0
        return f"{num_bytes:.1f} PB"

class FilePickerWindow(Adw.ApplicationWindow):
    def __init__(self, app):
        super().__init__(application=app, title="File Picker")
        self.set_default_size(600, 400)
        self._setup_ui()

    def _setup_ui(self):
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.set_content(main_box)
        header = Adw.HeaderBar()
        select_button = Gtk.Button(label="Select")
        select_button.add_css_class("suggested-action")
        select_button.connect("clicked", self.on_select_clicked)
        header.pack_start(select_button)
        main_box.append(header)

        self.file_model = Gio.ListStore.new(FileItem)
        sorter = Gtk.CustomSorter.new(self._sort_func)
        sort_model = Gtk.SortListModel.new(self.file_model, sorter)
        section_sorter = Gtk.CustomSorter.new(self._section_sort_func)
        sort_model.set_section_sorter(section_sorter)
        selection_model = Gtk.NoSelection(model=sort_model)
        file_factory = Gtk.SignalListItemFactory()
        file_factory.connect("setup", self.setup_file_row)
        file_factory.connect("bind", self.bind_file_row)
        header_factory = Gtk.SignalListItemFactory()
        header_factory.connect("setup", self.setup_header_row)
        header_factory.connect("bind", self.bind_header_row)
        self.listview = Gtk.ListView(
            model=selection_model,
            factory=file_factory,
            header_factory=header_factory
        )
        self.listview.set_show_separators(True)
        self.listview.connect("activate", self.on_list_activate)
        scrolled_window = Gtk.ScrolledWindow()
        scrolled_window.set_child(self.listview)
        scrolled_window.set_vexpand(True)
        main_box.append(scrolled_window)
        self.status_label = Gtk.Label(label="Waiting for input...")
        self.status_label.set_xalign(0)
        self.status_label.set_margin_start(12)
        self.status_label.set_margin_end(12)
        self.status_label.set_margin_top(6)
        self.status_label.set_margin_bottom(6)
        main_box.append(self.status_label)

    def _sort_func(self, item1, item2, user_data=None):
        group1 = item1.get_property("group_id")
        group2 = item2.get_property("group_id")
        if group1 < group2:
            return Gtk.Ordering.SMALLER
        elif group1 > group2:
            return Gtk.Ordering.LARGER
        else:
            return Gtk.Ordering.EQUAL

    def _section_sort_func(self, item1, item2, user_data=None):
        group1 = item1.get_property("group_id")
        group2 = item2.get_property("group_id")
        if group1 < group2:
            return Gtk.Ordering.SMALLER
        elif group1 > group2:
            return Gtk.Ordering.LARGER
        else:
            return Gtk.Ordering.EQUAL

    def setup_header_row(self, factory, listitem):
        widget = SectionHeaderWidget()
        listitem.set_child(widget)

    def bind_header_row(self, factory, listitem):
        widget = listitem.get_child()
        if widget:
            first_item = listitem.get_item()
            if first_item:
                group_id = first_item.get_property("group_id")
                widget.label.set_text(f"Group {group_id}")
            else:
                widget.label.set_text("Group")

    def setup_file_row(self, factory, listitem):
        widget = PickerRowWidget()
        listitem.set_child(widget)

    def bind_file_row(self, factory, listitem):
        fileinfo = listitem.get_item()
        widget = listitem.get_child()
        if fileinfo is None or widget is None:
            return
        if hasattr(listitem, "bindings"):
            for binding in listitem.bindings:
                binding.unbind()
        bindings = [
            fileinfo.bind_property("selected", widget.check, "active",
                                 GObject.BindingFlags.SYNC_CREATE | GObject.BindingFlags.BIDIRECTIONAL),
            fileinfo.bind_property("name", widget.name_label, "label",
                                 GObject.BindingFlags.SYNC_CREATE),
            fileinfo.bind_property("size", widget.size_label, "label",
                                 GObject.BindingFlags.SYNC_CREATE)
        ]
        listitem.bindings = bindings
        widget.set_file(fileinfo.get_property("name"), fileinfo.get_property("size"))

    def _start_parsing(self):
        def parse():
            GLib.idle_add(self.status_label.set_text, "Parsing input...")
            processed_groups = 0
            total_file_count = 0
            current_group_files = []
            for line in sys.stdin:
                line = line.rstrip("\n")
                if line == "":
                    if current_group_files:
                        self._process_group(current_group_files, processed_groups + 1)
                        total_file_count += len(current_group_files)
                        processed_groups += 1
                        GLib.idle_add(self.status_label.set_text, f"Processed {total_file_count} files in {processed_groups} groups...")
                        current_group_files = []
                else:
                    current_group_files.append(line)
            if current_group_files:
                self._process_group(current_group_files, processed_groups + 1)
                total_file_count += len(current_group_files)
                processed_groups += 1
            GLib.idle_add(self.status_label.set_text, f"{total_file_count} files in {processed_groups} groups.")
        threading.Thread(target=parse, daemon=True).start()

    def _process_group(self, files, group_count):
        items_to_add = []
        for file_path in files:
            try:
                size = os.path.getsize(file_path)
                size_str = PickerRowWidget.format_size(size)
            except Exception:
                size_str = "-"
            items_to_add.append(FileItem(file_path, size_str, group_count, False))
        GLib.idle_add(self._add_items_to_model, items_to_add)

    def _add_items_to_model(self, items):
        for item in items:
            self.file_model.append(item)

    def on_list_activate(self, listview, position):
        item = listview.get_model().get_item(position)
        if item:
            is_selected = item.get_property("selected")
            item.set_property("selected", not is_selected)

    def on_select_clicked(self, button):
        selected_files = []
        for i in range(self.file_model.get_n_items()):
            item = self.file_model.get_item(i)
            if item and item.get_property("selected"):
                selected_files.append(item.get_property("name"))
        for file in selected_files:
            print(file)
        self.get_application().quit()

class FilePickerApp(Adw.Application):
    def __init__(self):
        super().__init__(application_id="net.knoopx.filepicker")
    def do_activate(self):
        win = FilePickerWindow(self)
        win.present()
        win._start_parsing()

def main():
    app = FilePickerApp()
    app.run(sys.argv)

if __name__ == "__main__":
    main()
