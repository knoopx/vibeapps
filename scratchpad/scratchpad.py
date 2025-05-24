#!/usr/bin/env python

import re
import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw, Gio

class ScratchpadWindow(Adw.ApplicationWindow):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.set_default_size(600, 700)
        self.set_title("Scratchpad Calculator")

        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.set_content(main_box)

        header_bar = Adw.HeaderBar()
        main_box.append(header_bar)

        # Input Text View
        self.text_view = Gtk.TextView()
        self.text_view.set_vexpand(True)
        self.text_view.set_monospace(True)
        self.text_view.get_buffer().connect("changed", self.on_text_changed)

        input_scrolled_window = Gtk.ScrolledWindow()
        input_scrolled_window.set_child(self.text_view)
        input_scrolled_window.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        main_box.append(input_scrolled_window)

        # Results Label (placeholder)
        self.results_label = Gtk.Label(label="Results will appear here")
        self.results_label.set_vexpand(False)
        self.results_label.set_halign(Gtk.Align.END)
        self.results_label.set_css_classes(["title-4"]) # Adwaita style class
        main_box.append(self.results_label)


    def on_text_changed(self, buffer):
        text = buffer.get_text(buffer.get_start_iter(), buffer.get_end_iter(), False)
        lines = text.split('\n')
        results = []
        for line in lines:
            # Basic parsing: look for lines with numbers and simple operators
            # This is a very simplified parser and needs to be much more robust
            match = re.match(r"\s*([\d\.]+)\s*([\+\-\*\/])\s*([\d\.]+)\s*", line)
            if match:
                try:
                    num1 = float(match.group(1))
                    op = match.group(2)
                    num2 = float(match.group(3))
                    result = 0
                    if op == '+':
                        result = num1 + num2
                    elif op == '-':
                        result = num1 - num2
                    elif op == '*':
                        result = num1 * num2
                    elif op == '/':
                        if num2 != 0:
                            result = num1 / num2
                        else:
                            result = "Error: Division by zero"
                    results.append(f"{line} = {result}")
                except ValueError:
                    results.append(f"{line} = Error: Invalid number") # Should not happen with current regex
                except Exception as e:
                    results.append(f"{line} = Error: {e}")
            elif line.strip(): # If line is not empty and not a calculation
                results.append(line) # Keep the line as is
            else:
                results.append("") # Keep empty lines

        # For now, display the last valid result or the original line
        # A more sophisticated approach would be to display results next to each line
        if results:
            # Display all processed lines in the results label for now
            # A better UI would be to have a separate results view or inline results
            self.results_label.set_text("\n".join(results))
        else:
            self.results_label.set_text("Enter calculations...")


class ScratchpadApplication(Adw.Application):
    def __init__(self):
        super().__init__(application_id="com.example.ScratchpadCalculator",
                         flags=Gio.ApplicationFlags.FLAGS_NONE)

    def do_activate(self):
        win = self.props.active_window
        if not win:
            win = ScratchpadWindow(application=self)
        win.present()

    def do_startup(self):
        Adw.Application.do_startup(self)

if __name__ == "__main__":
    app = ScratchpadApplication()
    app.run(None)
