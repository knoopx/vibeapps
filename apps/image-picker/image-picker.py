#!/usr/bin/env python3

import sys
import os
import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
gi.require_version("GdkPixbuf", "2.0")
from gi.repository import Gtk, Adw, Gio, GLib, GdkPixbuf, Gdk
from gi.repository import GObject, Pango


class ImageItem(GObject.Object):
    __gtype_name__ = "ImagePickerImageItem"
    path = GObject.Property(type=str)
    selected = GObject.Property(type=bool, default=False)
    group_id = GObject.Property(type=int, default=0)

    def __init__(self, **kwargs):
        super().__init__()
        for key, value in kwargs.items():
            self.set_property(key, value)


class ImageThumbnailWidget(Gtk.Box):
    def __init__(self, image_item, group_row):
        self.group_row = group_row
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        self.image_item = image_item
        self.set_margin_top(12)
        self.set_margin_bottom(12)
        self.set_margin_start(12)
        self.set_margin_end(12)
        self.set_halign(Gtk.Align.CENTER)
        self.set_valign(Gtk.Align.CENTER)
        self.set_vexpand(False)

        # Thumbnail
        self.thumbnail = Gtk.Image()
        self.thumbnail.set_pixel_size(128)
        self.thumbnail.set_halign(Gtk.Align.CENTER)
        self.thumbnail.set_valign(Gtk.Align.CENTER)
        self.append(self.thumbnail)

        # Checkbox and label in a horizontal box
        hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        hbox.set_halign(Gtk.Align.CENTER)
        hbox.set_valign(Gtk.Align.CENTER)

        self.check = Gtk.CheckButton()
        self.check.set_can_focus(False)
        self.check.set_active(image_item.get_property("selected"))
        # Bind checkbox to image_item.selected property
        image_item.bind_property(
            "selected",
            self.check,
            "active",
            GObject.BindingFlags.BIDIRECTIONAL | GObject.BindingFlags.SYNC_CREATE,
        )
        self.check.set_halign(Gtk.Align.CENTER)
        self.check.set_valign(Gtk.Align.CENTER)
        self.check.set_margin_top(0)
        self.check.set_margin_bottom(0)
        self.check.set_margin_start(0)
        self.check.set_margin_end(0)
        hbox.append(self.check)

        # Vertical box for name and info
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        vbox.set_halign(Gtk.Align.CENTER)
        vbox.set_valign(Gtk.Align.CENTER)
        vbox.set_hexpand(False)
        vbox.set_vexpand(False)

        self.label = Gtk.Label(
            label=os.path.basename(image_item.get_property("path")), xalign=0.5
        )
        self.label.set_ellipsize(Pango.EllipsizeMode.END)
        self.label.set_width_chars(16)
        self.label.set_max_width_chars(16)
        self.label.set_hexpand(False)
        self.label.set_halign(Gtk.Align.CENTER)
        self.label.set_valign(Gtk.Align.CENTER)
        self.label.set_margin_top(0)
        self.label.set_margin_bottom(0)
        self.label.set_margin_start(0)
        self.label.set_margin_end(0)
        self.label.set_can_focus(True)
        vbox.append(self.label)
        # Make label clickable
        gesture = Gtk.GestureClick()
        gesture.connect("released", self.on_label_clicked)
        self.label.add_controller(gesture)

        # Make entire grid item clickable
        grid_gesture = Gtk.GestureClick()
        grid_gesture.connect("released", self.on_grid_clicked)
        self.add_controller(grid_gesture)
        # Keyboard navigation for label
        key_controller = Gtk.EventControllerKey()
        key_controller.connect("key-pressed", self.on_label_key_pressed)
        self.label.add_controller(key_controller)
        # Keyboard navigation for checkbox

        # File size and dimensions label
        self.info_label = Gtk.Label(label="", xalign=0.5)
        self.info_label.set_ellipsize(Pango.EllipsizeMode.END)
        self.info_label.set_width_chars(20)
        self.info_label.set_max_width_chars(20)
        self.info_label.set_hexpand(False)
        self.info_label.set_halign(Gtk.Align.CENTER)
        self.info_label.set_valign(Gtk.Align.CENTER)
        self.info_label.set_margin_top(0)
        self.info_label.set_margin_bottom(0)
        self.info_label.set_margin_start(0)
        self.info_label.set_margin_end(0)
        vbox.append(self.info_label)

        hbox.append(vbox)
        hbox.set_margin_top(4)
        self.append(hbox)

        self.update_thumbnail()

    def update_thumbnail(self):
        path = self.image_item.get_property("path")
        # File size and dimensions
        size_str = "? KB"
        dim_str = "?×?"
        try:
            if os.path.exists(path):
                size_bytes = os.path.getsize(path)
                if size_bytes < 1024 * 1024:
                    size_str = f"{size_bytes // 1024} KB"
                else:
                    size_str = f"{size_bytes / (1024 * 1024):.1f} MB"
            pixbuf = GdkPixbuf.Pixbuf.new_from_file(path)
            if pixbuf:
                dim_str = f"{pixbuf.get_width()}×{pixbuf.get_height()}"
        except Exception:
            pass
        self.info_label.set_text(f"{size_str} — {dim_str}")
        try:
            # GTK4: Use Gdk.Texture and set_from_paintable
            texture = GdkPixbuf.Pixbuf.new_from_file_at_size(path, 128, 128)
            if texture is not None:
                gdk_texture = Gdk.Texture.new_for_pixbuf(texture)
                self.thumbnail.set_from_paintable(gdk_texture)
                self.thumbnail.set_visible(True)
            else:
                self.thumbnail.clear()
                self.thumbnail.set_visible(False)
        except Exception:
            self.thumbnail.clear()
            self.thumbnail.set_visible(False)

    def on_check_toggled(self, check):
        self.image_item.set_property("selected", check.get_active())

    def on_label_clicked(self, gesture, n_press, x, y):
        # Toggle the checkbox
        self.check.set_active(not self.check.get_active())

    def on_grid_clicked(self, gesture, n_press, x, y):
        # Toggle the checkbox
        self.check.set_active(not self.check.get_active())

    def on_label_key_pressed(self, controller, keyval, keycode, state):
        # Space or Enter toggles the checkbox
        if keyval in (Gdk.KEY_space, Gdk.KEY_Return):
            self.check.set_active(not self.check.get_active())
            return True
        # Arrow key navigation
        return self.handle_arrow_key(keyval)

    def handle_arrow_key(self, keyval):
        # Find parent grid and this widget's index
        parent = self.get_parent()
        while parent and not isinstance(parent, Gtk.FlowBox):
            parent = parent.get_parent()
        if not parent:
            return False
        children = []
        child = parent.get_first_child()
        while child:
            children.append(child.get_child())
            child = child.get_next_sibling()
        idx = children.index(self)
        cols = parent.get_max_children_per_line()
        next_idx = None
        if keyval == Gdk.KEY_Right:
            next_idx = idx + 1 if idx + 1 < len(children) else None
        elif keyval == Gdk.KEY_Left:
            next_idx = idx - 1 if idx - 1 >= 0 else None
        elif keyval == Gdk.KEY_Down:
            next_idx = idx + cols if idx + cols < len(children) else None
            # If at last row, move to next group's header label
            if next_idx is None:
                next_group = self.group_row.get_next_group()
                if next_group:
                    # Focus the group label of the next group
                    next_group.get_children()[1].get_children()[1].grab_focus()
                    return True
        elif keyval == Gdk.KEY_Up:
            next_idx = idx - cols if idx - cols >= 0 else None
            # If at first row, move to previous group's header label
            if idx < cols:
                prev_group = self.group_row.get_prev_group()
                if prev_group:
                    prev_group.get_children()[1].get_children()[
                        1
                    ].grab_focus()  # group label
                    return True
            # If at first row but not first thumbnail, move to previous group's last thumbnail
            if next_idx is None:
                prev_group = self.group_row.get_prev_group()
                if prev_group and prev_group.thumbnails:
                    prev_group.thumbnails[-1].label.grab_focus()
                    return True
        elif keyval == Gdk.KEY_Down:
            next_idx = idx + cols if idx + cols < len(children) else None
            # If at last thumbnail, move to next group's group label
            if idx == len(children) - 1:
                next_group = self.group_row.get_next_group()
                if next_group:
                    next_group.get_children()[1].get_children()[
                        1
                    ].grab_focus()  # group label
                    return True
            if next_idx is None:
                next_group = self.group_row.get_next_group()
                if next_group and next_group.thumbnails:
                    next_group.thumbnails[0].label.grab_focus()
                    return True
        if next_idx is not None:
            # Focus the label of the next widget
            next_thumb = children[next_idx]
            next_thumb.label.grab_focus()
            return True
        return False


class ImageGroupRow(Gtk.Box):
    def __init__(self, group_id, image_items):
        self.group_id = group_id
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        self.set_hexpand(True)
        self.set_vexpand(False)
        self.set_margin_top(8)
        self.set_margin_bottom(8)
        self.set_margin_start(12)
        self.set_margin_end(12)
        header_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        group_check = Gtk.CheckButton()
        group_check.set_can_focus(True)
        group_check.set_halign(Gtk.Align.START)
        group_check.set_valign(Gtk.Align.CENTER)
        group_check.connect("toggled", self.on_group_check_toggled, image_items)
        header_box.append(group_check)

        self.group_check = group_check
        group_label = Gtk.Label(label=f"Group {group_id}", xalign=0)
        group_label.set_halign(Gtk.Align.START)
        group_label.set_valign(Gtk.Align.CENTER)
        group_label.set_can_focus(True)
        header_box.append(group_label)
        # Make group label clickable
        gesture = Gtk.GestureClick()
        gesture.connect("released", self.on_group_label_clicked)
        group_label.add_controller(gesture)
        # Keyboard navigation for group label
        key_controller = Gtk.EventControllerKey()
        key_controller.connect("key-pressed", self.on_group_label_key_pressed)
        group_label.add_controller(key_controller)

        header_box.set_margin_bottom(4)
        self.append(header_box)
        grid = Gtk.FlowBox()
        grid.set_max_children_per_line(6)
        grid.set_min_children_per_line(2)
        grid.set_selection_mode(Gtk.SelectionMode.NONE)
        grid.set_hexpand(True)
        grid.set_vexpand(False)
        grid.set_homogeneous(True)
        self.thumbnails = []
        for item in image_items:
            thumb = ImageThumbnailWidget(item, self)
            grid.append(thumb)
            self.thumbnails.append(thumb)

        grid.set_hexpand(True)
        grid.set_vexpand(False)
        self.append(grid)

    def get_next_group(self):
        parent = self.get_parent()
        if not parent:
            return None
        children = [
            child for child in parent.get_children() if isinstance(child, ImageGroupRow)
        ]
        idx = children.index(self)
        if idx + 1 < len(children):
            return children[idx + 1]
        return None

    def get_prev_group(self):
        parent = self.get_parent()
        if not parent:
            return None
        children = [
            child for child in parent.get_children() if isinstance(child, ImageGroupRow)
        ]
        idx = children.index(self)
        if idx - 1 >= 0:
            return children[idx - 1]
        return None
        grid.set_hexpand(True)
        grid.set_vexpand(False)
        self.append(grid)

    def on_group_check_toggled(self, check, image_items):
        checked = check.get_active()
        for thumb in self.thumbnails:
            thumb.check.set_active(checked)
        for item in image_items:
            item.set_property("selected", checked)

    def on_group_label_clicked(self, gesture, n_press, x, y):
        # Toggle the group checkbox
        self.group_check.set_active(not self.group_check.get_active())

    def on_group_label_key_pressed(self, controller, keyval, keycode, state):
        # Space or Enter toggles the group checkbox
        if keyval in (Gdk.KEY_space, Gdk.KEY_Return):
            self.group_check.set_active(not self.group_check.get_active())
            return True
        # Down arrow: focus first thumbnail label
        if keyval == Gdk.KEY_Down:
            if self.thumbnails:
                self.thumbnails[0].label.grab_focus()
                return True
        # Up arrow: focus previous group's last thumbnail label
        if keyval == Gdk.KEY_Up:
            prev_group = self.get_prev_group()
            if prev_group and prev_group.thumbnails:
                prev_group.thumbnails[-1].label.grab_focus()
                return True
        return False


class ImagePickerWindow(Adw.ApplicationWindow):
    def _register_actions(self):
        actions = {
            "invert_selection": self._invert_selection,
            "select_all": lambda: self._set_all_selected(True),
            "unselect_all": lambda: self._set_all_selected(False),
            "select_by_path_glob": lambda: self._select_path(True),
            "unselect_by_path_glob": lambda: self._select_path(False),
        }

        criteria = {
            "first": (self._select_first_last, self._unselect_first_last),
            "last": (self._select_first_last, self._unselect_first_last),
            "smallest_size": ("size", False),
            "largest_size": ("size", True),
            "smallest_image": ("image_area", False),
            "largest_image": ("image_area", True),
            "shortest_name": ("name_length", False),
            "largest_name": ("name_length", True),
            "first_created": ("ctime", False),
            "last_created": ("ctime", True),
            "first_modified": ("mtime", False),
            "last_modified": ("mtime", True),
        }

        from functools import partial

        for name, params in criteria.items():
            for prefix in ["select", "unselect"]:
                action_name = f"{prefix}_{name}"
                unselect = prefix == "unselect"
                if name in ["first", "last"]:
                    handler = partial(
                        (
                            self._unselect_first_last
                            if unselect
                            else self._select_first_last
                        ),
                        name == "last",
                    )
                else:
                    handler = partial(
                        self._select_by_criterion, params[0], params[1], unselect
                    )
                actions[action_name] = handler

        for name, handler in actions.items():
            action = Gio.SimpleAction.new(name, None)

            def on_activate(act, param, h=handler, n=name):
                print(f"Action triggered: {n}")
                h()

            action.connect("activate", on_activate)
            self.add_action(action)

    def _create_selection_submenu(self, action_prefix):
        menu = Gio.Menu()
        menu.append("By Path...", f"win.{action_prefix}_by_path_glob")
        date_menu = Gio.Menu()
        date_menu.append("Newest Image (Created)", f"win.{action_prefix}_last_created")
        date_menu.append("Oldest Image (Created)", f"win.{action_prefix}_first_created")
        date_menu.append(
            "Last Updated (Modified)", f"win.{action_prefix}_last_modified"
        )
        date_menu.append(
            "Least Updated (Modified)", f"win.{action_prefix}_first_modified"
        )
        menu.append_submenu(f"{action_prefix.capitalize()} By Date", date_menu)
        size_menu = Gio.Menu()
        size_menu.append("Largest File Size", f"win.{action_prefix}_largest_size")
        size_menu.append("Smallest File Size", f"win.{action_prefix}_smallest_size")
        menu.append_submenu(f"{action_prefix.capitalize()} By Size", size_menu)
        name_menu = Gio.Menu()
        name_menu.append("Longest Filename", f"win.{action_prefix}_largest_name")
        name_menu.append("Shortest Filename", f"win.{action_prefix}_shortest_name")
        menu.append_submenu(f"{action_prefix.capitalize()} By Name Length", name_menu)
        image_menu = Gio.Menu()
        image_menu.append(
            "Largest Image Dimensions", f"win.{action_prefix}_largest_image"
        )
        image_menu.append(
            "Smallest Image Dimensions", f"win.{action_prefix}_smallest_image"
        )
        menu.append_submenu(
            f"{action_prefix.capitalize()} By Image Dimensions", image_menu
        )
        menu.append(f"First in Group", f"win.{action_prefix}_first")
        menu.append(f"Last in Group", f"win.{action_prefix}_last")
        if action_prefix == "select":
            menu.append("All", "win.select_all")
        else:
            menu.append("All", "win.unselect_all")
        return menu

    def _set_all_selected(self, selected: bool):
        for group_items in self.image_items_by_group.values():
            for item in group_items:
                item.set_property("selected", selected)

    def _invert_selection(self):
        for group_items in self.image_items_by_group.values():
            for item in group_items:
                current = item.get_property("selected")
                item.set_property("selected", not current)

    def _select_path(self, selected: bool):
        dialog = Adw.AlertDialog()
        dialog.set_heading("By Path")
        dialog.set_body("Enter a glob pattern (e.g. *.jpg, */foo/*.png):")
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

                for group_items in self.image_items_by_group.values():
                    for item in group_items:
                        path = item.get_property("path")
                        if fnmatch.fnmatch(path, pattern):
                            item.set_property("selected", selected)
            alert_dialog.close()

        dialog.connect("response", on_response)
        dialog.present(self)

    def _select_first_last(self, reverse: bool):
        for group_items in self.image_items_by_group.values():
            if group_items:
                idx = -1 if reverse else 0
                group_items[idx].set_property("selected", True)

    def _unselect_first_last(self, reverse: bool):
        for group_items in self.image_items_by_group.values():
            if group_items:
                idx = -1 if reverse else 0
                group_items[idx].set_property("selected", False)

    def _select_by_criterion(self, key_prop, reverse, unselect):
        for group_items in self.image_items_by_group.values():
            best_item = None
            best_val = float("-inf") if reverse else float("inf")
            for item in group_items:
                if key_prop == "size":
                    try:
                        val = os.path.getsize(item.get_property("path"))
                    except Exception:
                        val = -1
                elif key_prop == "image_area":
                    try:
                        pixbuf = GdkPixbuf.Pixbuf.new_from_file(
                            item.get_property("path")
                        )
                        if pixbuf is not None:
                            val = pixbuf.get_width() * pixbuf.get_height()
                        else:
                            val = -1
                    except Exception:
                        val = -1
                elif key_prop == "name_length":
                    val = len(os.path.basename(item.get_property("path")))
                elif key_prop == "ctime":
                    try:
                        val = os.stat(item.get_property("path")).st_ctime
                    except Exception:
                        val = -1
                elif key_prop == "mtime":
                    try:
                        val = os.stat(item.get_property("path")).st_mtime
                    except Exception:
                        val = -1
                else:
                    val = -1
                if val < 0:
                    continue
                if (reverse and val > best_val) or (not reverse and val < best_val):
                    best_val = val
                    best_item = item
            if best_item:
                print(
                    f"Selecting image: {best_item.get_property('path')} (criterion: {key_prop}, value: {best_val}, unselect: {unselect})"
                )
                best_item.set_property("selected", not unselect)

    def __init__(self, app):
        super().__init__(application=app, title="Image Picker")
        self.set_default_size(1200, 700)
        self.main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.main_box.set_hexpand(True)
        self.main_box.set_vexpand(True)
        self.set_content(self.main_box)
        header = Adw.HeaderBar()
        select_button = Gtk.Button(label="Select")
        select_button.add_css_class("suggested-action")
        select_button.connect("clicked", self.on_select_clicked)
        header.pack_start(select_button)

        # Quick selection menu button
        menu_button = Gtk.MenuButton.new()
        menu_button.set_icon_name("view-list-symbolic")
        menu = Gio.Menu()
        menu.append_submenu("Select", self._create_selection_submenu("select"))
        menu.append_submenu("Unselect", self._create_selection_submenu("unselect"))
        menu.append("Invert Selection", "win.invert_selection")
        menu_button.set_menu_model(menu)
        header.pack_end(menu_button)

        self.main_box.append(header)

        # Register actions
        self._register_actions()

        self.groups_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.groups_box.set_hexpand(True)
        self.groups_box.set_vexpand(False)
        groups_scrolled = Gtk.ScrolledWindow()
        groups_scrolled.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        groups_scrolled.set_hexpand(True)
        groups_scrolled.set_vexpand(True)
        groups_scrolled.set_child(self.groups_box)
        self.main_box.append(groups_scrolled)
        self.status_label = Gtk.Label(label="Waiting for input...")
        self.status_label.set_xalign(0)
        self.status_label.set_margin_start(12)
        self.status_label.set_margin_end(12)
        self.status_label.set_margin_top(6)
        self.status_label.set_margin_bottom(6)
        self.main_box.append(self.status_label)
        self.image_items_by_group = {}
        self._start_parsing()

    def _start_parsing(self):
        def parse():
            GLib.idle_add(self.status_label.set_text, "Parsing input...")
            processed_groups = 0
            total_image_count = 0
            current_group_images = []
            for line in sys.stdin:
                line = line.rstrip("\n")
                if line == "":
                    if current_group_images:
                        self._process_group(current_group_images, processed_groups + 1)
                        total_image_count += len(current_group_images)
                        processed_groups += 1
                        GLib.idle_add(
                            self.status_label.set_text,
                            f"Processed {total_image_count} images in {processed_groups} groups...",
                        )
                        current_group_images = []
                else:
                    current_group_images.append(line)
            if current_group_images:
                self._process_group(current_group_images, processed_groups + 1)
                total_image_count += len(current_group_images)
                processed_groups += 1
            GLib.idle_add(
                self.status_label.set_text,
                f"{total_image_count} images in {processed_groups} groups.",
            )

        import threading

        threading.Thread(target=parse, daemon=True).start()

    def _process_group(self, images, group_count):
        def is_image_file(path):
            image_exts = {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp", ".tiff"}
            ext = os.path.splitext(path)[1].lower()
            return ext in image_exts

        items = [
            ImageItem(path=img, group_id=group_count)
            for img in images
            if is_image_file(img)
        ]
        self.image_items_by_group[group_count] = items
        GLib.idle_add(self._add_group_row, group_count, items)

    def _add_group_row(self, group_id, items):
        row = ImageGroupRow(group_id, items)
        self.groups_box.append(row)

    def on_select_clicked(self, button):
        selected_images = []
        for group_items in self.image_items_by_group.values():
            for item in group_items:
                if item.get_property("selected"):
                    selected_images.append(item.get_property("path"))
        for img in selected_images:
            print(img)
        app = self.get_application()
        if app is not None:
            app.quit()


class ImagePickerApp(Adw.Application):
    def __init__(self):
        super().__init__(application_id="net.knoopx.imagepicker")

    def do_activate(self):
        win = ImagePickerWindow(self)
        win.present()


def main():
    app = ImagePickerApp()
    app.run(sys.argv)


if __name__ == "__main__":
    main()
