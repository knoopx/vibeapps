#!/usr/bin/env python

import os
import sys
import gi
import subprocess

gi.require_version("Adw", "1")
gi.require_version("Gtk", "4.0")
from gi.repository import Gtk, Gdk, GdkPixbuf, Gio, GLib, Adw


class ImageCaptionViewer(Adw.ApplicationWindow):  # Use Adw.ApplicationWindow
    def __init__(self, app, dataset_dir, caption_ext):
        super().__init__(application=app, title="Image/Caption Dataset Viewer")
        self.dataset_dir = dataset_dir
        self.caption_ext = caption_ext
        self.image_files = self._get_image_files()
        self.current_index = 0
        self.original_pixbuf = None

        self.set_default_size(800, 600)
        self.set_margin_start(0)   # Remove default window padding
        self.set_margin_end(0)     # Remove default window padding
        self.set_margin_top(0)     # Remove default window padding
        self.set_margin_bottom(0)  # Remove default window padding

        # Main layout using Adw.Clamp for centered content
        # self.clamp = Adw.Clamp() # Remove clamp
        self.layout = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        self.layout.set_hexpand(True)  # Allow children to expand horizontally
        self.layout.set_vexpand(True)  # Allow children to expand vertically
        # self.clamp.set_child(self.layout) # Remove clamp child setting
        # self.clamp.set_vexpand(True) # Remove clamp vexpand setting
        self.set_content(self.layout) # Set layout directly as content

        # Image display area
        self.picture = Gtk.Picture()
        self.picture.set_can_shrink(True)
        self.picture.set_vexpand(True)
        self.picture.set_hexpand(True)
        self.layout.append(self.picture)

        # Caption display area
        self.caption_label = Gtk.Label()
        self.caption_label.set_wrap(True)
        self.caption_label.set_margin_start(10)  # Add margin to caption label
        self.caption_label.set_margin_end(10)    # Add margin to caption label
        self.caption_label.set_margin_top(10)    # Add margin to caption label
        self.caption_label.set_margin_bottom(10) # Add margin to caption label
        self.caption_label.set_hexpand(True)     # Make label take full width
        self.caption_label.set_halign(Gtk.Align.CENTER)  # Align text within the label
        self.layout.append(self.caption_label)

        # Set up key event controller
        key_controller = Gtk.EventControllerKey()
        key_controller.connect("key-pressed", self.on_key_press)
        self.add_controller(key_controller)

        # Load the first image and caption if available
        if self.image_files:
            self.load_image_and_caption(self.current_index)
        else:
            self.caption_label.set_text("No images found in the specified directory.")

    def _get_image_files(self):
        """Retrieve all image files with a corresponding caption file in the dataset directory."""
        files = os.listdir(self.dataset_dir)
        image_files = [
            f for f in files if f.lower().endswith((".png", ".jpg", ".jpeg"))
        ]
        image_files = [
            f
            for f in image_files
            if os.path.exists(
                os.path.join(
                    self.dataset_dir, f"{os.path.splitext(f)[0]}{self.caption_ext}"
                )
            )
        ]
        return sorted(image_files)

    def load_image_and_caption(self, index):
        """Load the image and corresponding caption at the specified index."""
        image_file = self.image_files[index]
        image_path = os.path.join(self.dataset_dir, image_file)
        caption_path = os.path.join(
            self.dataset_dir, f"{os.path.splitext(image_file)[0]}{self.caption_ext}"
        )

        try:
            self.picture.set_filename(image_path)
        except gi.repository.GLib.Error as e:
            print(f"Error loading image {image_path}: {e}")
            self.picture.set_filename(None)
            self.caption_label.set_text(f"Error loading image: {e}")
            return

        try:
            with open(caption_path, "r") as f:
                caption = f.read().strip()
            self.caption_label.set_text(caption)
        except FileNotFoundError:
            self.caption_label.set_text("[No caption found]")
        except Exception as e:
            self.caption_label.set_text(f"[Error loading caption: {e}]")

    def on_key_press(self, controller, keyval, keycode, state):
        if keyval == Gdk.KEY_Right:
            self.next_image()
        elif keyval == Gdk.KEY_Left:
            self.prev_image()
        elif keyval == Gdk.KEY_Return:
            self.edit_caption()
        elif keyval == Gdk.KEY_Escape:
            self.close()

    def edit_caption(self):
        """Open the current caption file with the default text editor."""
        if not self.image_files:
            return

        image_file = self.image_files[self.current_index]
        caption_path = os.path.join(
            self.dataset_dir, f"{os.path.splitext(image_file)[0]}{self.caption_ext}"
        )
        try:
            # Use a more robust way to open files cross-platform if needed,
            # but xdg-open is standard on many Linux systems.
            subprocess.run(["xdg-open", caption_path])
        except FileNotFoundError:
            print(f"Error: 'xdg-open' command not found. Cannot open {caption_path}.")
        except Exception as e:
            print(f"Error launching editor for {caption_path}: {e}")

    def next_image(self):
        if self.current_index < len(self.image_files) - 1:
            self.current_index += 1
            self.load_image_and_caption(self.current_index)

    def prev_image(self):
        if self.current_index > 0:
            self.current_index -= 1
            self.load_image_and_caption(self.current_index)


class ImageViewerApp(Adw.Application):  # Use Adw.Application
    def __init__(self, dataset_dir, caption_ext):
        super().__init__(
            application_id="com.example.dataset-viewer",
            flags=Gio.ApplicationFlags.HANDLES_COMMAND_LINE
        )
        self.dataset_dir = dataset_dir
        self.caption_ext = caption_ext
        self.window = None

    def do_activate(self):
        if not self.window:
            self.window = ImageCaptionViewer(self, self.dataset_dir, self.caption_ext)
        self.window.present()

    def do_command_line(self, command_line):
        self.activate()
        return 0


def main():
    if len(sys.argv) < 2:
        print("Usage: dataset-viewer <dataset_directory> [caption_extension]")
        sys.exit(1)

    dataset_dir = sys.argv[1]
    caption_ext = sys.argv[2] if len(sys.argv) > 2 else ".txt"

    if not os.path.isdir(dataset_dir):
        print(f"Error: {dataset_dir} is not a valid directory.")
        sys.exit(1)

    app = ImageViewerApp(dataset_dir, caption_ext)
    app.run([])  # Remove sys.argv since we handle args in __init__


if __name__ == "__main__":
    main()