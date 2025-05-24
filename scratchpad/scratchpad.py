#!/usr/bin/env python

"""
Enhanced Scratchpad Calculator

Features:
- Basic arithmetic: +, -, *, /, ^, %
- Parentheses for precedence
- Constants: pi, e
- Functions: sqrt(), abs(), round(), floor(), ceil(), sin(), cos(), tan(), log(), ln()
- Variables: assign with 'variable = expression'
- Enhanced error handling with descriptive messages
"""

import re
import math
import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Gdk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw, Gio


class ScratchpadWindow(Adw.ApplicationWindow):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Initialize variables storage
        self.variables = {}

        self.set_default_size(800, 700)  # Increased default width for two panes
        self.set_title("Scratchpad")

        main_vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.set_content(main_vbox)

        header_bar = Adw.HeaderBar()
        main_vbox.append(header_bar)

        # Paned view for input and results
        paned = Gtk.Paned(orientation=Gtk.Orientation.HORIZONTAL)
        paned.set_vexpand(True)
        main_vbox.append(paned)

        # --- Left Pane: Input Text View ---
        self.text_view = Gtk.TextView()
        self.text_view.set_vexpand(True)
        self.text_view.set_monospace(True)
        self.text_view.get_buffer().connect("changed", self.on_text_changed)

        input_scrolled_window = Gtk.ScrolledWindow()
        input_scrolled_window.set_child(self.text_view)
        input_scrolled_window.set_policy(
            Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC
        )
        # Add some margin to the input text view
        self.text_view.set_left_margin(5)
        self.text_view.set_right_margin(5)
        self.text_view.set_top_margin(5)
        self.text_view.set_bottom_margin(5)

        paned.set_start_child(input_scrolled_window)

        # --- Right Pane: Results Text View ---
        self.results_view = Gtk.TextView()
        self.results_view.set_vexpand(True)
        self.results_view.set_editable(False)  # Results are not editable
        self.results_view.set_cursor_visible(False)  # No cursor in results
        self.results_view.set_monospace(True)  # Match input font style
        # Add some margin to the results text view
        self.results_view.set_left_margin(5)
        self.results_view.set_right_margin(5)
        self.results_view.set_top_margin(5)
        self.results_view.set_bottom_margin(5)

        results_scrolled_window = Gtk.ScrolledWindow()
        results_scrolled_window.set_child(self.results_view)
        results_scrolled_window.set_policy(
            Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC
        )
        paned.set_end_child(results_scrolled_window)

        # Set equal panel sizes using GTK's layout system
        paned.set_resize_start_child(True)
        paned.set_resize_end_child(True)
        paned.set_shrink_start_child(False)
        paned.set_shrink_end_child(False)

        # Create text tag for error formatting using CSS-based approach
        self.results_buffer = self.results_view.get_buffer()

        # Apply CSS for error styling that uses semantic colors
        self._setup_error_styling()

        # Listen for theme changes to reapply styling
        settings = Gtk.Settings.get_default()
        settings.connect("notify::gtk-theme-name", self._on_theme_changed)
        settings.connect("notify::gtk-application-prefer-dark-theme", self._on_theme_changed)

    def _setup_error_styling(self):
        """Setup error text styling using text tag properties"""
        # Create text tag for error formatting
        self.error_tag = self.results_buffer.create_tag("error")

        # Set error color - using Catppuccin Mocha red for consistency
        self.error_tag.set_property("foreground", "#f38ba8")

    def safe_eval(self, expression):
        """Safely evaluate mathematical expressions with enhanced functionality"""
        # Create a safe namespace with math functions and constants
        safe_namespace = {
            '__builtins__': {},
            # Basic math operations
            'abs': abs,
            'round': round,
            'min': min,
            'max': max,
            # Math functions
            'sqrt': math.sqrt,
            'floor': math.floor,
            'ceil': math.ceil,
            'sin': math.sin,
            'cos': math.cos,
            'tan': math.tan,
            'log': math.log10,
            'ln': math.log,
            # Constants
            'pi': math.pi,
            'e': math.e,
            # Power operator replacement
            'pow': pow,
        }

        # Add user-defined variables
        safe_namespace.update(self.variables)

        # Replace ^ with ** for power operations
        expression = expression.replace('^', '**')

        return eval(expression, safe_namespace)

    def parse_line(self, line):
        """Parse a line and determine if it's an assignment, expression, or comment"""
        line = line.strip()

        # Skip empty lines and comments
        if not line or line.startswith('#'):
            return None, None, ""

        # Check for variable assignment
        assignment_match = re.match(r'^\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*=\s*(.+)', line)
        if assignment_match:
            var_name, expression = assignment_match.groups()
            return 'assignment', var_name, expression

        # Otherwise treat as expression
        return 'expression', None, line

    def on_text_changed(self, buffer):
        text = buffer.get_text(buffer.get_start_iter(), buffer.get_end_iter(), False)
        lines = text.splitlines()

        # Clear the results buffer
        self.results_buffer.set_text("")

        # Reset variables for each full evaluation
        self.variables = {}

        for i, line in enumerate(lines):
            try:
                line_type, var_name, expression = self.parse_line(line)

                if line_type is None:
                    # Empty line or comment
                    self._append_result_line("")
                    continue

                if line_type == 'assignment':
                    # Variable assignment
                    try:
                        result = self.safe_eval(expression)
                        self.variables[var_name] = result

                        # Format result for display
                        if isinstance(result, float) and result.is_integer():
                            self._append_result_line(f"{var_name} = {int(result)}")
                        else:
                            self._append_result_line(f"{var_name} = {result}")
                    except Exception as e:
                        self._append_error_line(str(e))

                elif line_type == 'expression':
                    # Mathematical expression
                    try:
                        result = self.safe_eval(expression)

                        # Format result to avoid unnecessary .0 for whole numbers
                        if isinstance(result, float) and result.is_integer():
                            self._append_result_line(str(int(result)))
                        else:
                            self._append_result_line(str(result))
                    except ZeroDivisionError:
                        self._append_error_line("Division by zero")
                    except NameError as e:
                        self._append_error_line(f"Undefined variable - {str(e)}")
                    except SyntaxError:
                        self._append_error_line("Invalid syntax")
                    except ValueError as e:
                        self._append_error_line(f"Invalid value - {str(e)}")
                    except Exception as e:
                        self._append_error_line(str(e))

            except Exception as e:
                self._append_error_line(str(e))

    def _append_result_line(self, text):
        """Append a normal result line to the results buffer"""
        end_iter = self.results_buffer.get_end_iter()
        if not self.results_buffer.get_char_count() == 0:
            self.results_buffer.insert(end_iter, "\n")
            end_iter = self.results_buffer.get_end_iter()
        self.results_buffer.insert(end_iter, text)

    def _append_error_line(self, text):
        """Append an error line in red to the results buffer"""
        end_iter = self.results_buffer.get_end_iter()
        if not self.results_buffer.get_char_count() == 0:
            self.results_buffer.insert(end_iter, "\n")
            end_iter = self.results_buffer.get_end_iter()
        self.results_buffer.insert_with_tags(end_iter, text, self.error_tag)

    def _on_theme_changed(self, settings, pspec):
        """Handle theme changes and refresh styling"""
        # Update error tag styling for the new theme
        if hasattr(self, 'error_tag'):
            # Refresh error color - you could make this more sophisticated
            # to detect light/dark theme and adjust colors accordingly
            self.error_tag.set_property("foreground", "#f38ba8")

        # Refresh the results display
        buffer = self.text_view.get_buffer()
        self.on_text_changed(buffer)


class ScratchpadApplication(Adw.Application):
    def __init__(self):
        super().__init__(
            application_id="com.example.ScratchpadCalculator",
            flags=Gio.ApplicationFlags.FLAGS_NONE,
        )

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
