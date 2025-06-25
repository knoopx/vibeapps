#!/usr/bin/env python
import os
import sys
import gi
gi.require_version('Adw', '1')
gi.require_version('Gtk', '4.0')
from gi.repository import Gtk, Gdk, Gio, Adw

class ImageCaptionViewer(Adw.ApplicationWindow):

    def __init__(self, app, dataset_dir, caption_ext):
        super().__init__(application=app, title='Image/Caption Dataset Viewer')
        self.dataset_dir = dataset_dir
        self.caption_ext = caption_ext
        self.image_files = self._get_image_files()
        self.current_index = 0
        self.set_default_size(800, 600)
        self.set_margin_start(0)
        self.set_margin_end(0)
        self.set_margin_top(0)
        self.set_margin_bottom(0)
        self.layout = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        self.layout.set_hexpand(True)
        self.layout.set_vexpand(True)
        self.set_content(self.layout)
        self.picture = Gtk.Picture()
        self.picture.set_can_shrink(True)
        self.picture.set_vexpand(True)
        self.picture.set_hexpand(True)
        self.layout.append(self.picture)

        # Create scrolled window for text view
        self.caption_scrolled = Gtk.ScrolledWindow()
        self.caption_scrolled.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        self.caption_scrolled.set_margin_start(10)
        self.caption_scrolled.set_margin_end(10)
        self.caption_scrolled.set_margin_top(10)
        self.caption_scrolled.set_margin_bottom(10)
        self.caption_scrolled.set_hexpand(True)
        self.caption_scrolled.set_size_request(-1, 100)

        # Create text view for editing captions
        self.caption_textview = Gtk.TextView()
        self.caption_textview.set_wrap_mode(Gtk.WrapMode.WORD)
        self.caption_textview.set_hexpand(True)
        self.caption_buffer = self.caption_textview.get_buffer()
        self.caption_buffer.connect('changed', self.on_caption_changed)

        self.caption_scrolled.set_child(self.caption_textview)
        self.layout.append(self.caption_scrolled)

        key_controller = Gtk.EventControllerKey()
        key_controller.set_propagation_phase(Gtk.PropagationPhase.CAPTURE)

        key_controller.connect('key-pressed', self.on_key_press)
        self.add_controller(key_controller)

        if self.image_files:
            self.load_image_and_caption(self.current_index)
        else:
            self.caption_buffer.set_text('No images found in the specified directory.')

    def _get_image_files(self):
        files = os.listdir(self.dataset_dir)
        image_files = [f for f in files if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
        image_files = [f for f in image_files if os.path.exists(os.path.join(self.dataset_dir, f'{os.path.splitext(f)[0]}{self.caption_ext}'))]
        return sorted(image_files)

    def load_image_and_caption(self, index):
        image_file = self.image_files[index]
        image_path = os.path.join(self.dataset_dir, image_file)
        caption_path = os.path.join(self.dataset_dir, f'{os.path.splitext(image_file)[0]}{self.caption_ext}')
        try:
            self.picture.set_filename(image_path)
        except gi.repository.GLib.Error as e:
            print(f'Error loading image {image_path}: {e}')
            self.picture.set_filename(None)
            self.caption_buffer.set_text(f'Error loading image: {e}')
            return
        try:
            with open(caption_path, 'r') as f:
                caption = f.read().strip()
            self.caption_buffer.set_text(caption)
        except FileNotFoundError:
            self.caption_buffer.set_text('[No caption found]')
        except Exception as e:
            self.caption_buffer.set_text(f'[Error loading caption: {e}]')

    def on_caption_changed(self, buffer):
        """Auto-save caption when text changes"""
        if not self.image_files or not hasattr(self, 'current_index'):
            return

        image_file = self.image_files[self.current_index]
        caption_path = os.path.join(self.dataset_dir, f'{os.path.splitext(image_file)[0]}{self.caption_ext}')

        start_iter = buffer.get_start_iter()
        end_iter = buffer.get_end_iter()
        caption_text = buffer.get_text(start_iter, end_iter, False)

        try:
            with open(caption_path, 'w') as f:
                f.write(caption_text)
        except Exception as e:
            print(f'Error saving caption to {caption_path}: {e}')

    def on_key_press(self, controller, keyval, keycode, state):
        if keyval == Gdk.KEY_Right and state & Gdk.ModifierType.CONTROL_MASK:
            self.next_image()
        elif keyval == Gdk.KEY_Left and state & Gdk.ModifierType.CONTROL_MASK:
            self.prev_image()
        elif keyval == Gdk.KEY_Delete:
            self.delete_current_image()
        elif keyval == Gdk.KEY_Escape:
            self.close()

    def next_image(self):
        if self.current_index < len(self.image_files) - 1:
            self.current_index += 1
            self.load_image_and_caption(self.current_index)

    def prev_image(self):
        if self.current_index > 0:
            self.current_index -= 1
            self.load_image_and_caption(self.current_index)

    def delete_current_image(self):
        """Delete the current image and caption files after confirmation"""
        if not self.image_files:
            return

        image_file = self.image_files[self.current_index]
        image_path = os.path.join(self.dataset_dir, image_file)
        caption_path = os.path.join(self.dataset_dir, f'{os.path.splitext(image_file)[0]}{self.caption_ext}')

        # Create confirmation dialog
        dialog = Adw.MessageDialog.new(self, "Delete Image and Caption?")
        dialog.set_body(image_file)
        dialog.add_response("cancel", "Cancel")
        dialog.add_response("delete", "Delete")
        dialog.set_response_appearance("delete", Adw.ResponseAppearance.DESTRUCTIVE)
        dialog.set_default_response("cancel")
        dialog.set_close_response("cancel")

        def on_response(dialog, response):
            if response == "delete":
                try:
                    # Remove image file
                    if os.path.exists(image_path):
                        os.remove(image_path)

                    # Remove caption file
                    if os.path.exists(caption_path):
                        os.remove(caption_path)

                    # Remove from the list
                    self.image_files.pop(self.current_index)

                    # Navigate to next image or adjust index
                    if not self.image_files:
                        # No images left
                        self.picture.set_filename(None)
                        self.caption_buffer.set_text('No images remaining in dataset.')
                        self.current_index = 0
                    elif self.current_index >= len(self.image_files):
                        # We were at the last image, go to the new last image
                        self.current_index = len(self.image_files) - 1
                        self.load_image_and_caption(self.current_index)
                    else:
                        # Load the next image (which now has the same index)
                        self.load_image_and_caption(self.current_index)

                except Exception as e:
                    # Show error dialog
                    error_dialog = Adw.MessageDialog.new(self, "Error Deleting Files")
                    error_dialog.set_body(f"Failed to delete files:\n{str(e)}")
                    error_dialog.add_response("ok", "OK")
                    error_dialog.set_default_response("ok")
                    error_dialog.present()

        dialog.connect("response", on_response)
        dialog.present()

class ImageViewerApp(Adw.Application):

    def __init__(self, dataset_dir, caption_ext):
        super().__init__(application_id='net.knoopx.dataset-viewer', flags=Gio.ApplicationFlags.HANDLES_COMMAND_LINE)
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
        print('Usage: dataset-viewer <dataset_directory> [caption_extension]')
        sys.exit(1)
    dataset_dir = sys.argv[1]
    caption_ext = sys.argv[2] if len(sys.argv) > 2 else '.tags'
    if not os.path.isdir(dataset_dir):
        print(f'Error: {dataset_dir} is not a valid directory.')
        sys.exit(1)
    app = ImageViewerApp(dataset_dir, caption_ext)
    app.run([])

if __name__ == '__main__':
    main()