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

        self.input_scrolled_window = Gtk.ScrolledWindow()
        self.input_scrolled_window.set_child(self.text_view)
        self.input_scrolled_window.set_policy(
            Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC
        )
        # Add some margin to the input text view
        self.text_view.set_left_margin(5)
        self.text_view.set_right_margin(5)
        self.text_view.set_top_margin(5)
        self.text_view.set_bottom_margin(5)

        paned.set_start_child(self.input_scrolled_window)

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

        self.results_scrolled_window = Gtk.ScrolledWindow()
        self.results_scrolled_window.set_child(self.results_view)
        self.results_scrolled_window.set_policy(
            Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC
        )
        paned.set_end_child(self.results_scrolled_window)

        # Set equal panel sizes using GTK's layout system
        paned.set_resize_start_child(True)
        paned.set_resize_end_child(True)
        paned.set_shrink_start_child(False)
        paned.set_shrink_end_child(False)

        # Create text tag for error formatting using CSS-based approach
        self.results_buffer = self.results_view.get_buffer()

        # Apply CSS for error styling that uses semantic colors
        self._setup_error_styling()

        # Setup scroll synchronization
        self._setup_scroll_sync()

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

    def _setup_scroll_sync(self):
        """Setup scroll synchronization between input and results panels"""
        # Flag to prevent infinite scroll loops
        self._syncing_scroll = False

        # Get the vertical adjustments for both scroll windows
        self.input_vadj = self.input_scrolled_window.get_vadjustment()
        self.results_vadj = self.results_scrolled_window.get_vadjustment()

        # Connect scroll events
        self.input_vadj.connect("value-changed", self._on_input_scroll)
        self.results_vadj.connect("value-changed", self._on_results_scroll)

    def _on_input_scroll(self, adjustment):
        """Sync results panel scroll when input panel scrolls"""
        if not self._syncing_scroll:
            self._syncing_scroll = True
            self.results_vadj.set_value(adjustment.get_value())
            self._syncing_scroll = False

    def _on_results_scroll(self, adjustment):
        """Sync input panel scroll when results panel scrolls"""
        if not self._syncing_scroll:
            self._syncing_scroll = True
            self.input_vadj.set_value(adjustment.get_value())
            self._syncing_scroll = False

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

        # Handle trailing newline: if text ends with newline, add empty line to match text view behavior
        if text.endswith('\n'):
            lines.append('')

        # Ensure we always have at least one line to work with
        if not lines:
            lines = [""]

        # Clear the results buffer
        self.results_buffer.set_text("")

        # Reset variables for each full evaluation
        self.variables = {}

        # Process each line and build results
        results = []
        for i, line in enumerate(lines):
            try:
                line_type, var_name, expression = self.parse_line(line)

                if line_type is None:
                    # Empty line or comment
                    results.append("")
                    continue

                if line_type == 'assignment':
                    # Variable assignment
                    try:
                        result = self.safe_eval(expression)
                        self.variables[var_name] = result

                        # Format result for display
                        if isinstance(result, float) and result.is_integer():
                            results.append(f"{var_name} = {int(result)}")
                        else:
                            results.append(f"{var_name} = {result}")
                    except Exception as e:
                        results.append(str(e))

                elif line_type == 'expression':
                    # Mathematical expression
                    try:
                        result = self.safe_eval(expression)

                        # Format result to avoid unnecessary .0 for whole numbers
                        if isinstance(result, float) and result.is_integer():
                            results.append(str(int(result)))
                        else:
                            results.append(str(result))
                    except ZeroDivisionError:
                        results.append("Division by zero")
                    except NameError as e:
                        results.append(f"Undefined variable - {str(e)}")
                    except SyntaxError:
                        results.append("Invalid syntax")
                    except ValueError as e:
                        results.append(f"Invalid value - {str(e)}")
                    except Exception as e:
                        results.append(str(e))

            except Exception as e:
                results.append(str(e))

        # Set the results text all at once to ensure proper line count matching
        self._set_results_text(lines, results)

    def _set_results_text(self, input_lines, results):
        """Set the results text ensuring line count matches input"""
        # Ensure results list has exactly the same length as input lines
        while len(results) < len(input_lines):
            results.append("")

        # Clear the results buffer
        self.results_buffer.set_text("")

        # Build the complete results text with proper formatting
        for i, (input_line, result_text) in enumerate(zip(input_lines, results)):
            if i > 0:
                self._append_result_line_raw("\n")

            # Check if this result should be shown as an error
            line_type, _, _ = self.parse_line(input_line)
            is_error = self._is_error_result(result_text, line_type)

            if is_error:
                self._append_error_line_raw(result_text)
            else:
                self._append_result_line_raw(result_text)

    def _is_error_result(self, result_text, line_type):
        """Determine if a result should be displayed as an error"""
        if not result_text or line_type is None:
            return False

        # Check for common error patterns
        error_patterns = [
            "Division by zero",
            "Undefined variable",
            "Invalid syntax",
            "Invalid value",
            "NameError:",
            "SyntaxError:",
            "ValueError:",
            "ZeroDivisionError:",
            "TypeError:"
        ]

        return any(pattern in result_text for pattern in error_patterns)

    def _append_result_line_raw(self, text):
        """Append text to results buffer without adding newlines"""
        end_iter = self.results_buffer.get_end_iter()
        self.results_buffer.insert(end_iter, text)

    def _append_error_line_raw(self, text):
        """Append error text to results buffer without adding newlines"""
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
