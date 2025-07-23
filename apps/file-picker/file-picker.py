#!/usr/bin/env python3

import sys
import os
import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
gi.require_version("GdkPixbuf", "2.0")
from gi.repository import Gtk, Adw, Gio, GLib, Gdk, GdkPixbuf

import threading
from gi.repository import GObject, Pango

from functools import partial


@GObject.type_register
class FileItem(GObject.Object):
    __gtype_name__ = "FilePickerFileItem"
    name = GObject.Property(type=str)
    size = GObject.Property(type=str)
    selected = GObject.Property(type=bool, default=False)
    group_id = GObject.Property(type=int, default=0)
    # Cached properties for performance
    file_size = GObject.Property(type=GObject.TYPE_INT64, default=-1)
    ctime = GObject.Property(type=float, default=-1.0)
    mtime = GObject.Property(type=float, default=-1.0)
    image_area = GObject.Property(type=int, default=-1)
    name_length = GObject.Property(type=int, default=0)

    def __init__(self, **kwargs):
        super().__init__()
        for key, value in kwargs.items():
            self.set_property(key, value)


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
        self.name_label.set_ellipsize(Pango.EllipsizeMode.START)
        self.name_label.set_max_width_chars(120)
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
        bounds = self.check.get_bounds()
        if not (
            bounds.x <= x <= bounds.x + bounds.width
            and bounds.y <= y <= bounds.y + bounds.height
        ):
            self.check.set_active(not self.check.get_active())

    def set_file(self, file_path, size_str):
        self.name_label.set_text(file_path)
        self.size_label.set_text(size_str)
        if PickerRowWidget.is_image_file(file_path):
            try:
                pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_size(file_path, 32, 32)
                self.thumbnail.set_from_pixbuf(pixbuf)
                self.thumbnail.set_visible(True)
            except Exception:
                self.thumbnail.clear()
                self.thumbnail.set_visible(False)
        else:
            self.thumbnail.clear()
            self.thumbnail.set_visible(False)

    @staticmethod
    def is_image_file(file_path):
        image_exts = {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp", ".tiff"}
        ext = os.path.splitext(file_path)[1].lower()
        return ext in image_exts

    @staticmethod
    def format_size(num_bytes):
        if num_bytes < 0:
            return "-"
        for unit in ["B", "KB", "MB", "GB", "TB", "PB"]:
            if num_bytes < 1024.0:
                return f"{num_bytes:.1f} {unit}" if unit != "B" else f"{num_bytes} B"
            num_bytes /= 1024.0
        return f"{num_bytes:.1f} PB"


class FilePickerWindow(Adw.ApplicationWindow):
    def select_indices(self, indices: set):
        for i in indices:
            item = self.file_model.get_item(i)
            if item:
                item.set_property("selected", True)

    def unselect_indices(self, indices: set):
        for i in indices:
            item = self.file_model.get_item(i)
            if item:
                item.set_property("selected", False)

    def invert_selection(self):
        for i in range(self.file_model.get_n_items()):
            item = self.file_model.get_item(i)
            if item:
                current = item.get_property("selected")
                item.set_property("selected", not current)

    def set_all_selected(self, selected: bool):
        for i in range(self.file_model.get_n_items()):
            item = self.file_model.get_item(i)
            if item:
                item.set_property("selected", selected)

    def select_path(self, selected: bool):
        dialog = Adw.AlertDialog()
        dialog.set_heading("By Path")
        dialog.set_body("Enter a glob pattern (e.g. *.jpg, */foo/*.txt):")
        entry = Gtk.Entry()
        dialog.set_extra_child(entry)
        dialog.add_response("ok", "OK")
        dialog.add_response("cancel", "Cancel")
        dialog.set_default_response("ok")
        dialog.set_close_response("cancel")

        def on_response(alert_dialog, response):
            if response == "ok":
                pattern = entry.get_text()
                import fnmatch

                for i in range(self.file_model.get_n_items()):
                    item = self.file_model.get_item(i)
                    if item:
                        path = item.get_property("name")
                        if fnmatch.fnmatch(path, pattern):
                            item.set_property("selected", selected)
            alert_dialog.close()

        dialog.connect("response", on_response)
        dialog.present(self)

    def _handle_first_last(self, reverse: bool, unselect: bool = False):
        indices = set()
        for group_id in self._get_group_ids():
            items = self._get_items_in_group(group_id)
            if items:
                idx = items[-1][0] if reverse else items[0][0]
                indices.add(idx)
        if unselect:
            self.unselect_indices(indices)
        else:
            self.select_indices(indices)

    def select_first_last(self, reverse: bool):
        self._handle_first_last(reverse, unselect=False)

    def unselect_first_last(self, reverse: bool):
        self._handle_first_last(reverse, unselect=True)

    def _select_by_criterion(self, key_prop, reverse, unselect):
        indices = set()
        for group_id in self._get_group_ids():
            items_in_group = self._get_items_in_group(group_id)
            if not items_in_group:
                continue

            best_item_idx = -1
            best_val = float("-inf") if reverse else float("inf")

            for i, item in items_in_group:
                val = item.get_property(key_prop)
                if key_prop in ["file_size", "image_area", "ctime", "mtime"] and val < 0:
                    continue

                if (reverse and val > best_val) or (not reverse and val < best_val):
                    best_val = val
                    best_item_idx = i

            if best_item_idx != -1:
                indices.add(best_item_idx)

        if unselect:
            self.unselect_indices(indices)
        else:
            self.select_indices(indices)

    def _register_actions(self):
        actions = {
            "invert_selection": self.invert_selection,
            "select_all": partial(self.set_all_selected, True),
            "select_none": partial(self.set_all_selected, False),
            "select_by_path_glob": partial(self.select_path, True),
            "unselect_by_path_glob": partial(self.select_path, False),
        }

        criteria = {
            "first": (self.select_first_last, self.unselect_first_last),
            "last": (self.select_first_last, self.unselect_first_last),
            "smallest_size": ("file_size", False),
            "largest_size": ("file_size", True),
            "smallest_image": ("image_area", False),
            "largest_image": ("image_area", True),
            "shortest_name": ("name_length", False),
            "largest_name": ("name_length", True),
            "first_created": ("ctime", False),
            "last_created": ("ctime", True),
            "first_modified": ("mtime", False),
            "last_modified": ("mtime", True),
        }

        for name, params in criteria.items():
            for prefix in ["select", "unselect"]:
                action_name = f"{prefix}_{name}"
                unselect = prefix == "unselect"
                if name in ["first", "last"]:
                    handler = partial(params[0 if not unselect else 1], name == "last")
                else:
                    handler = partial(
                        self._select_by_criterion, params[0], params[1], unselect
                    )
                actions[action_name] = handler

        for name, handler in actions.items():
            action = Gio.SimpleAction.new(name, None)
            action.connect("activate", lambda a, p, h=handler: h())
            self.add_action(action)

    def __init__(self, app):
        super().__init__(application=app, title="File Picker")
        self.set_default_size(600, 400)
        self._register_actions()
        self._setup_ui()

    def _create_selection_submenu(self, action_prefix):
        menu = Gio.Menu()
        menu.append("By Path...", f"win.{action_prefix}_by_path_glob")
        date_menu = Gio.Menu()
        date_menu.append("Newest File (Created)", f"win.{action_prefix}_last_created")
        date_menu.append("Oldest File (Created)", f"win.{action_prefix}_first_created")
        date_menu.append("Last Updated (Modified)", f"win.{action_prefix}_last_modified")
        date_menu.append(
            "Least Updated (Modified)", f"win.{action_prefix}_first_modified"
        )
        menu.append_submenu("By Date", date_menu)
        size_menu = Gio.Menu()
        size_menu.append("Largest File Size", f"win.{action_prefix}_largest_size")
        size_menu.append("Smallest File Size", f"win.{action_prefix}_smallest_size")
        menu.append_submenu("By Size", size_menu)
        name_menu = Gio.Menu()
        name_menu.append("Longest Filename", f"win.{action_prefix}_largest_name")
        name_menu.append("Shortest Filename", f"win.{action_prefix}_shortest_name")
        menu.append_submenu("By Name Length", name_menu)
        image_menu = Gio.Menu()
        image_menu.append(
            "Largest Image Dimensions", f"win.{action_prefix}_largest_image"
        )
        image_menu.append(
            "Smallest Image Dimensions", f"win.{action_prefix}_smallest_image"
        )
        menu.append_submenu("By Image Dimensions", image_menu)
        menu.append("First in Group", f"win.{action_prefix}_first")
        menu.append("Last in Group", f"win.{action_prefix}_last")
        if action_prefix == "select":
            menu.append("All", "win.select_all")
        else:
            menu.append("All", "win.select_none")
        return menu

    def _setup_ui(self):
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.set_content(main_box)
        header = Adw.HeaderBar()
        select_button = Gtk.Button(label="Select")
        select_button.add_css_class("suggested-action")
        select_button.connect("clicked", self.on_select_clicked)
        header.pack_start(select_button)

        menu_button = Gtk.MenuButton.new()
        menu_button.set_icon_name("view-list-symbolic")
        menu = Gio.Menu()
        menu.append_submenu("Select", self._create_selection_submenu("select"))
        menu.append_submenu("Unselect", self._create_selection_submenu("unselect"))
        menu.append("Invert Selection", "win.invert_selection")
        menu_button.set_menu_model(menu)
        header.pack_end(menu_button)
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
            model=selection_model, factory=file_factory, header_factory=header_factory
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
            fileinfo.bind_property(
                "selected",
                widget.check,
                "active",
                GObject.BindingFlags.SYNC_CREATE | GObject.BindingFlags.BIDIRECTIONAL,
            ),
            fileinfo.bind_property(
                "name", widget.name_label, "label", GObject.BindingFlags.SYNC_CREATE
            ),
            fileinfo.bind_property(
                "size", widget.size_label, "label", GObject.BindingFlags.SYNC_CREATE
            ),
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
                        GLib.idle_add(
                            self.status_label.set_text,
                            f"Processed {total_file_count} files in {processed_groups} groups...",
                        )
                        current_group_files = []
                else:
                    current_group_files.append(line)
            if current_group_files:
                self._process_group(current_group_files, processed_groups + 1)
                total_file_count += len(current_group_files)
                processed_groups += 1
            GLib.idle_add(
                self.status_label.set_text,
                f"{total_file_count} files in {processed_groups} groups.",
            )

        threading.Thread(target=parse, daemon=True).start()

    def _process_group(self, files, group_count):
        items_to_add = []
        for file_path in files:
            item_props = {
                "name": file_path,
                "size": "-",
                "group_id": group_count,
                "selected": False,
                "file_size": -1,
                "ctime": -1.0,
                "mtime": -1.0,
                "image_area": -1,
                "name_length": len(os.path.basename(file_path)),
            }
            try:
                stat = os.stat(file_path)
                item_props.update(
                    {
                        "file_size": stat.st_size,
                        "size": PickerRowWidget.format_size(stat.st_size),
                        "ctime": stat.st_ctime,
                        "mtime": stat.st_mtime,
                    }
                )
                if PickerRowWidget.is_image_file(file_path):
                    try:
                        pixbuf = GdkPixbuf.Pixbuf.new_from_file(file_path)
                        if pixbuf:
                            item_props["image_area"] = (
                                pixbuf.get_width() * pixbuf.get_height()
                            )
                    except Exception:
                        item_props["image_area"] = -1
            except FileNotFoundError:
                item_props["name"] = f"[Not Found] {file_path}"
            except Exception:
                pass  # Keep default error values
            items_to_add.append(FileItem(**item_props))
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
        app = self.get_application()
        if app is not None:
            app.quit()

    def _get_group_ids(self):
        group_ids = set()
        for i in range(self.file_model.get_n_items()):
            item = self.file_model.get_item(i)
            if item is not None:
                group_ids.add(item.get_property("group_id"))
        return sorted(group_ids)

    def _get_items_in_group(self, group_id):
        items = []
        for i in range(self.file_model.get_n_items()):
            item = self.file_model.get_item(i)
            if item is not None and item.get_property("group_id") == group_id:
                items.append((i, item))
        return items


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

