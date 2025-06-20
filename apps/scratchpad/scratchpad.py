#!/usr/bin/env python
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
        self.variables = {}
        self.set_default_size(800, 700)
        self.set_title("Scratchpad")
        main_vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.set_content(main_vbox)
        header_bar = Adw.HeaderBar()
        main_vbox.append(header_bar)
        paned = Gtk.Paned(orientation=Gtk.Orientation.HORIZONTAL)
        paned.set_vexpand(True)
        main_vbox.append(paned)
        self.text_view = Gtk.TextView()
        self.text_view.set_vexpand(True)
        self.text_view.set_monospace(True)
        self.text_view.get_buffer().connect("changed", self.on_text_changed)
        self.input_scrolled_window = Gtk.ScrolledWindow()
        self.input_scrolled_window.set_child(self.text_view)
        self.input_scrolled_window.set_policy(
            Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC
        )
        self.text_view.set_left_margin(5)
        self.text_view.set_right_margin(5)
        self.text_view.set_top_margin(5)
        self.text_view.set_bottom_margin(5)
        paned.set_start_child(self.input_scrolled_window)
        self.results_view = Gtk.TextView()
        self.results_view.set_vexpand(True)
        self.results_view.set_editable(False)
        self.results_view.set_cursor_visible(False)
        self.results_view.set_monospace(True)
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
        paned.set_resize_start_child(True)
        paned.set_resize_end_child(True)
        paned.set_shrink_start_child(False)
        paned.set_shrink_end_child(False)
        self.results_buffer = self.results_view.get_buffer()
        self._setup_error_styling()
        self._setup_scroll_sync()

    def _setup_error_styling(self):
        self.error_tag = self.results_buffer.create_tag("error")
        self.error_tag.set_property("foreground", "#ff0000")

    def _setup_scroll_sync(self):
        self._syncing_scroll = False
        self.input_vadj = self.input_scrolled_window.get_vadjustment()
        self.results_vadj = self.results_scrolled_window.get_vadjustment()
        self.input_vadj.connect("value-changed", self._on_input_scroll)
        self.results_vadj.connect("value-changed", self._on_results_scroll)

    def _on_input_scroll(self, adjustment):
        if not self._syncing_scroll:
            self._syncing_scroll = True
            self.results_vadj.set_value(adjustment.get_value())
            self._syncing_scroll = False

    def _on_results_scroll(self, adjustment):
        if not self._syncing_scroll:
            self._syncing_scroll = True
            self.input_vadj.set_value(adjustment.get_value())
            self._syncing_scroll = False

    def safe_eval(self, expression):
        safe_namespace = {
            "__builtins__": {},
            # Basic math
            "abs": abs,
            "round": round,
            "min": min,
            "max": max,
            "sum": sum,
            "len": len,
            "pow": pow,
            "sqrt": math.sqrt,
            "floor": math.floor,
            "ceil": math.ceil,
            "sin": math.sin,
            "cos": math.cos,
            "tan": math.tan,
            "log": math.log10,
            "ln": math.log,
            "pi": math.pi,
            "e": math.e,
            "bin": lambda x: bin(int(x))[
                2:
            ],  # Binary representation (without 0b prefix)
            "hex": lambda x: hex(int(x))[
                2:
            ],  # Hexadecimal representation (without 0x prefix)
            "oct": lambda x: oct(int(x))[
                2:
            ],  # Octal representation (without 0o prefix)
            "log2": math.log2,  # Logarithm base 2
            "gcd": math.gcd,  # Greatest common divisor
            "lcm": lambda x, y: (
                abs(int(x) * int(y)) // math.gcd(int(x), int(y))
                if x != 0 and y != 0
                else 0
            ),  # Least common multiple
            "factorial": math.factorial,
            "avg": lambda *args: sum(args) / len(args) if args else 0,
            "median": lambda *args: sorted(args)[len(args) // 2] if args else 0,
            # Programming constants
            "kb": 1024,  # Kilobyte
            "mb": 1024**2,  # Megabyte
            "gb": 1024**3,  # Gigabyte
            "tb": 1024**4,  # Terabyte
            # Time & date calculations (in seconds/minutes/hours/days)
            "seconds": 1,
            "minutes": 60,
            "hours": 3600,
            "days": 86400,
            "weeks": 604800,
            "years": 31536000,
        }
        safe_namespace.update(self.variables)
        expression = expression.replace("^", "**")
        return eval(expression, safe_namespace)

    def parse_line(self, line):
        line = line.strip()
        if not line or line.startswith("#"):
            return (None, None, "")
        assignment_match = re.match("^\\s*([a-zA-Z_][a-zA-Z0-9_]*)\\s*=\\s*(.+)", line)
        if assignment_match:
            var_name, expression = assignment_match.groups()
            return ("assignment", var_name, expression)
        return ("expression", None, line)

    def on_text_changed(self, buffer):
        text = buffer.get_text(buffer.get_start_iter(), buffer.get_end_iter(), False)
        lines = text.splitlines()
        if text.endswith("\n"):
            lines.append("")
        if not lines:
            lines = [""]
        self.results_buffer.set_text("")
        self.variables = {}
        results = []
        for i, line in enumerate(lines):
            try:
                line_type, var_name, expression = self.parse_line(line)
                if line_type is None:
                    results.append("")
                    continue
                if line_type == "assignment":
                    try:
                        result = self.safe_eval(expression)
                        self.variables[var_name] = result
                        if isinstance(result, float) and result.is_integer():
                            results.append(f"{var_name} = {int(result)}")
                        else:
                            results.append(f"{var_name} = {result}")
                    except Exception as e:
                        results.append(str(e))
                elif line_type == "expression":
                    try:
                        result = self.safe_eval(expression)
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
        self._set_results_text(lines, results)

    def _set_results_text(self, input_lines, results):
        while len(results) < len(input_lines):
            results.append("")
        self.results_buffer.set_text("")
        for i, (input_line, result_text) in enumerate(zip(input_lines, results)):
            if i > 0:
                self._append_result_line_raw("\n")
            line_type, _, _ = self.parse_line(input_line)
            is_error = self._is_error_result(result_text, line_type)
            if is_error:
                self._append_error_line_raw(result_text)
            else:
                self._append_result_line_raw(result_text)

    def _is_error_result(self, result_text, line_type):
        if not result_text or line_type is None:
            return False
        error_patterns = [
            "Division by zero",
            "Undefined variable",
            "Invalid syntax",
            "Invalid value",
            "NameError:",
            "SyntaxError:",
            "ValueError:",
            "ZeroDivisionError:",
            "TypeError:",
        ]
        return any((pattern in result_text for pattern in error_patterns))

    def _append_result_line_raw(self, text):
        end_iter = self.results_buffer.get_end_iter()
        self.results_buffer.insert(end_iter, text)

    def _append_error_line_raw(self, text):
        end_iter = self.results_buffer.get_end_iter()
        self.results_buffer.insert_with_tags(end_iter, text, self.error_tag)


class ScratchpadApplication(Adw.Application):

    def __init__(self):
        super().__init__(
            application_id="net.knoopx.scratchpad",
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
