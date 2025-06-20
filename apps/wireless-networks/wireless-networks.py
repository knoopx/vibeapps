#!/usr/bin/env python3
import gi
import subprocess
import threading
import sys
import re
from typing import Optional, Dict, Any

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw, GLib, GObject, Gio, Pango
from picker_window import PickerWindow, PickerItem

APP_ID = "net.knoopx.wireless-networks"


class WiFiNetwork(PickerItem):
    __gtype_name__ = "WiFiNetwork"

    ssid = GObject.Property(type=str, default="")
    bssid = GObject.Property(type=str, default="")
    mode = GObject.Property(type=str, default="")
    channel = GObject.Property(type=str, default="")
    rate = GObject.Property(type=str, default="")
    signal = GObject.Property(type=int, default=0)
    bars = GObject.Property(type=str, default="")
    security = GObject.Property(type=str, default="")
    active = GObject.Property(type=bool, default=False)
    in_use = GObject.Property(type=bool, default=False)

    def __init__(self, network_data: Dict[str, Any]):
        super().__init__()
        self.ssid = network_data.get("SSID", "").strip()
        self.bssid = network_data.get("BSSID", "").strip()
        self.mode = network_data.get("MODE", "").strip()
        self.channel = network_data.get("CHAN", "").strip()
        self.rate = network_data.get("RATE", "").strip()
        self.signal = self._parse_signal(network_data.get("SIGNAL", "0"))
        self.bars = network_data.get("BARS", "").strip()
        self.security = network_data.get("SECURITY", "").strip()
        self.active = network_data.get("ACTIVE", "").strip().lower() == "yes"
        self.in_use = network_data.get("IN-USE", "").strip() == "*"

    def _parse_signal(self, signal_str: str) -> int:
        """Parse signal strength from string like '75' or '75 %'"""
        try:
            # Remove any non-numeric characters and parse as int
            numbers = re.findall(r'-?\d+', signal_str)
            if numbers:
                signal = int(numbers[0])
                # Convert negative dBm to percentage (rough approximation)
                if signal < 0:
                    # Convert dBm to percentage: -30dBm = excellent, -90dBm = poor
                    signal = max(0, min(100, 2 * (signal + 100)))
                return signal
            return 0
        except (ValueError, AttributeError):
            return 0

    def get_signal_icon(self) -> str:
        """Get appropriate signal strength icon"""
        if self.signal >= 80:
            return "network-wireless-signal-excellent-symbolic"
        elif self.signal >= 60:
            return "network-wireless-signal-good-symbolic"
        elif self.signal >= 40:
            return "network-wireless-signal-ok-symbolic"
        elif self.signal >= 20:
            return "network-wireless-signal-weak-symbolic"
        else:
            return "network-wireless-signal-none-symbolic"

    def get_security_icon(self) -> str:
        """Get appropriate security icon"""
        if self.security and self.security != "--":
            if "WPA3" in self.security or "WPA2" in self.security:
                return "network-wireless-encrypted-symbolic"
            elif "WEP" in self.security:
                return "security-medium-symbolic"
            else:
                return "security-high-symbolic"
        else:
            return "network-wireless-symbolic"

    def __eq__(self, other):
        if not isinstance(other, WiFiNetwork):
            return False
        return self.bssid == other.bssid

    def __hash__(self):
        return hash(self.bssid)


class WirelessNetworksWindow(PickerWindow):

    def __init__(self, **kwargs):
        self._current_networks = []
        self._filtered_networks = []
        self._refresh_thread = None
        self._should_refresh = True
        self._password_dialog = None
        super().__init__(
            title="Wireless Networks", search_placeholder="Search by SSID...", **kwargs
        )

    def get_item_type(self):
        return WiFiNetwork

    def load_initial_data(self):
        self._refresh_networks()

    def on_search_changed(self, query):
        if not query.strip():
            self.on_search_cleared()
            return

        query_lower = query.lower()
        filtered = []
        for network in self._current_networks:
            if (
                query_lower in network.ssid.lower()
                or query_lower in network.bssid.lower()
                or query_lower in network.security.lower()
            ):
                filtered.append(network)

        self._filtered_networks = filtered
        self._update_ui()

    def on_search_cleared(self):
        self._filtered_networks = self._current_networks[:]
        self._update_ui()

    def on_item_activated(self, item):
        if not item or not item.ssid:
            return

        if item.in_use:
            # Already connected, show details
            self._show_network_details(item)
        else:
            # Try to connect
            self._connect_to_network(item)

    def setup_list_item(self, list_item):
        main_box = Gtk.Box(
            orientation=Gtk.Orientation.HORIZONTAL,
            spacing=12,
            margin_top=8,
            margin_bottom=8,
            margin_start=12,
            margin_end=12,
        )

        # Signal strength icon
        signal_icon = Gtk.Image()
        signal_icon.set_pixel_size(20)

        # Network info
        info_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        info_box.set_hexpand(True)

        # SSID and security
        header_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        ssid_label = Gtk.Label(halign=Gtk.Align.START, xalign=0)
        ssid_label.set_ellipsize(Pango.EllipsizeMode.END)
        ssid_label.add_css_class("heading")

        security_icon = Gtk.Image()
        security_icon.set_pixel_size(14)

        header_box.append(ssid_label)
        header_box.append(security_icon)

        # Details line
        details_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        security_label = Gtk.Label(halign=Gtk.Align.START, xalign=0)
        security_label.add_css_class("caption")
        security_label.set_opacity(0.7)

        channel_label = Gtk.Label(halign=Gtk.Align.START, xalign=0)
        channel_label.add_css_class("caption")
        channel_label.set_opacity(0.7)

        details_box.append(security_label)
        details_box.append(channel_label)

        info_box.append(header_box)
        info_box.append(details_box)

        # Signal strength percentage
        signal_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        signal_box.set_valign(Gtk.Align.CENTER)

        signal_label = Gtk.Label(halign=Gtk.Align.END, xalign=1)
        signal_label.add_css_class("caption")
        signal_label.set_width_chars(6)

        signal_box.append(signal_label)

        main_box.append(signal_icon)
        main_box.append(info_box)
        main_box.append(signal_box)

        list_item.set_child(main_box)

    def bind_list_item(self, list_item, item):
        main_box = list_item.get_child()
        if not main_box:
            return

        # Get widgets by walking the hierarchy
        child = main_box.get_first_child()
        signal_icon = child

        child = child.get_next_sibling() if child else None
        info_box = child

        child = child.get_next_sibling() if child else None
        signal_box = child

        if not info_box:
            return

        # Get info box children
        header_box = info_box.get_first_child()
        if not header_box:
            return

        details_box = header_box.get_next_sibling()

        # Get header box children
        ssid_label = header_box.get_first_child()
        security_icon = ssid_label.get_next_sibling() if ssid_label else None

        # Get details box children
        if details_box:
            security_label = details_box.get_first_child()
            channel_label = (
                security_label.get_next_sibling() if security_label else None
            )
        else:
            security_label = None
            channel_label = None

        # Get signal box children
        signal_label = signal_box.get_first_child() if signal_box else None

        # Bind data
        if ssid_label:
            ssid_text = item.ssid or "Hidden Network"
            ssid_label.set_text(ssid_text)

            # Make active connections bold
            if item.in_use:
                ssid_label.add_css_class("heading")
                ssid_label.set_markup(f"<b>{GLib.markup_escape_text(ssid_text)}</b>")
            else:
                ssid_label.remove_css_class("heading")
                ssid_label.set_text(ssid_text)

        # Signal icon
        if signal_icon:
            signal_icon.set_from_icon_name(item.get_signal_icon())

        # Security icon
        if security_icon:
            security_icon.set_from_icon_name(item.get_security_icon())

        # Security text
        if security_label:
            security_text = (
                item.security if item.security and item.security != "--" else "Open"
            )
            security_label.set_text(security_text)

        # Channel
        if channel_label:
            if item.channel and item.channel.strip():
                channel_str = item.channel.strip()
                # Channel should be a simple decimal number
                channel_text = f"Ch {channel_str}"
            else:
                channel_text = ""
            channel_label.set_text(channel_text)

        # Signal strength
        if signal_label:
            signal_label.set_text(f"{item.signal}%")

    def get_empty_icon(self):
        return "network-wireless-symbolic"

    def get_loading_icon(self):
        return "network-wireless-acquiring-symbolic"

    def get_empty_title(self):
        return "No Wireless Networks Found"

    def get_empty_description(self):
        return "Make sure wireless is enabled and try refreshing."

    def get_context_menu_model(self, item) -> Optional[Gio.Menu]:
        if not item or not item.ssid:
            return None

        menu_model = Gio.Menu.new()

        if item.in_use:
            menu_model.append("Disconnect", "context.on_disconnect_action")
            menu_model.append("Show Details", "context.on_show_details_action")
        else:
            menu_model.append("Connect", "context.on_connect_action")

        menu_model.append("Copy SSID", "context.on_copy_ssid_action")
        menu_model.append("Copy BSSID", "context.on_copy_bssid_action")
        menu_model.append("Forget Network", "context.on_forget_network_action")

        return menu_model

    def get_global_context_menu_model(self) -> Optional[Gio.Menu]:
        menu_model = Gio.Menu.new()
        menu_model.append("Refresh Networks", "global.on_refresh_action")
        menu_model.append("Enable WiFi", "global.on_enable_wifi_action")
        menu_model.append("Disable WiFi", "global.on_disable_wifi_action")
        return menu_model

    def get_global_context_menu_actions(self) -> dict:
        return {
            "on_refresh_action": "on_refresh_action",
            "on_enable_wifi_action": "on_enable_wifi_action",
            "on_disable_wifi_action": "on_disable_wifi_action",
        }

    # Context menu actions
    def on_connect_action(self, action, param):
        selected_item = self.get_selected_item()
        if selected_item:
            self._connect_to_network(selected_item)

    def on_disconnect_action(self, action, param):
        selected_item = self.get_selected_item()
        if selected_item:
            self._disconnect_from_network(selected_item)

    def on_show_details_action(self, action, param):
        selected_item = self.get_selected_item()
        if selected_item:
            self._show_network_details(selected_item)

    def on_copy_ssid_action(self, action, param):
        selected_item = self.get_selected_item()
        if selected_item:
            clipboard = self.get_clipboard()
            clipboard.set(selected_item.ssid)

    def on_copy_bssid_action(self, action, param):
        selected_item = self.get_selected_item()
        if selected_item:
            clipboard = self.get_clipboard()
            clipboard.set(selected_item.bssid)

    def on_forget_network_action(self, action, param):
        selected_item = self.get_selected_item()
        if selected_item:
            self._forget_network(selected_item)

    # Global actions
    def on_refresh_action(self, action, param):
        self._refresh_networks()

    def on_enable_wifi_action(self, action, param):
        self._run_nmcli_command(["radio", "wifi", "on"])
        GLib.timeout_add(1000, self._refresh_networks)

    def on_disable_wifi_action(self, action, param):
        self._run_nmcli_command(["radio", "wifi", "off"])
        GLib.timeout_add(1000, self._refresh_networks)

    def _show_network_details(self, item):
        dialog = Adw.MessageDialog.new(self, f"WiFi Network Details: {item.ssid}")

        details = f"""
<b>SSID:</b> {GLib.markup_escape_text(item.ssid)}
<b>BSSID:</b> {GLib.markup_escape_text(item.bssid)}
<b>Security:</b> {GLib.markup_escape_text(item.security or 'Open')}
<b>Signal:</b> {item.signal}% ({item.bars})
<b>Channel:</b> {item.channel}
<b>Rate:</b> {item.rate}
<b>Status:</b> {'Connected' if item.in_use else 'Available'}
        """.strip()

        dialog.set_body_use_markup(True)
        dialog.set_body(details)
        dialog.add_response("close", "Close")
        dialog.set_default_response("close")
        dialog.present()

    def _connect_to_network(self, item):
        """Connect to a WiFi network"""
        if item.security and item.security != "--":
            # Network requires password
            self._show_password_dialog(item)
        else:
            # Open network, connect directly
            self._perform_connection(item.ssid, None)

    def _show_password_dialog(self, item):
        """Show password input dialog"""
        dialog = Adw.MessageDialog.new(self, f"Connect to {item.ssid}")
        dialog.set_body("This network requires a password.")

        # Create password entry
        content_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        content_box.set_margin_top(12)
        content_box.set_margin_bottom(12)
        content_box.set_margin_start(12)
        content_box.set_margin_end(12)

        password_entry = Gtk.PasswordEntry()
        # password_entry.set_placeholder_text('Enter network password')  # May not be available in older GTK
        password_entry.set_show_peek_icon(True)

        content_box.append(password_entry)
        dialog.set_extra_child(content_box)

        dialog.add_response("cancel", "Cancel")
        dialog.add_response("connect", "Connect")
        dialog.set_response_appearance("connect", Adw.ResponseAppearance.SUGGESTED)
        dialog.set_default_response("connect")

        def on_response(dialog, response):
            if response == "connect":
                password = password_entry.get_text()
                self._perform_connection(item.ssid, password)
            dialog.destroy()

        dialog.connect("response", on_response)
        password_entry.connect("activate", lambda entry: dialog.response("connect"))
        dialog.present()

        # Focus password entry after dialog is shown
        GLib.idle_add(password_entry.grab_focus)

    def _perform_connection(self, ssid, password):
        """Perform the actual connection"""

        def connect_thread():
            try:
                cmd = ["nmcli", "device", "wifi", "connect", ssid]
                if password:
                    cmd.extend(["password", password])

                result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

                GLib.idle_add(
                    self._on_connection_result,
                    ssid,
                    result.returncode == 0,
                    result.stderr,
                )
            except subprocess.TimeoutExpired:
                GLib.idle_add(
                    self._on_connection_result, ssid, False, "Connection timeout"
                )
            except Exception as e:
                GLib.idle_add(self._on_connection_result, ssid, False, str(e))

        thread = threading.Thread(target=connect_thread, daemon=True)
        thread.start()

    def _on_connection_result(self, ssid, success, error_msg):
        """Handle connection result"""
        if success:
            self._show_toast(f"Connected to {ssid}")
        else:
            error_dialog = Adw.MessageDialog.new(self, "Connection Failed")
            error_dialog.set_body(f"Failed to connect to {ssid}.\n\n{error_msg}")
            error_dialog.add_response("ok", "OK")
            error_dialog.present()

        # Refresh networks to update status
        GLib.timeout_add(1000, self._refresh_networks)

    def _disconnect_from_network(self, item):
        """Disconnect from current network"""

        def disconnect_thread():
            try:
                wifi_interface = self._get_wifi_interface()
                if wifi_interface is None:
                    GLib.idle_add(self._show_wifi_interface_error, "disconnect")
                    return

                result = subprocess.run(
                    ["nmcli", "device", "disconnect", wifi_interface],
                    capture_output=True,
                    text=True,
                    timeout=10,
                )
                GLib.idle_add(
                    self._on_disconnection_result, item.ssid, result.returncode == 0
                )
            except Exception:
                GLib.idle_add(self._on_disconnection_result, item.ssid, False)

        thread = threading.Thread(target=disconnect_thread, daemon=True)
        thread.start()

    def _on_disconnection_result(self, ssid, success):
        """Handle disconnection result"""
        if success:
            self._show_toast(f"Disconnected from {ssid}")

        # Refresh networks to update status
        GLib.timeout_add(1000, self._refresh_networks)

    def _forget_network(self, item):
        """Forget a saved network"""
        dialog = Adw.MessageDialog.new(self, "Forget Network")
        dialog.set_body(f'Are you sure you want to forget the network "{item.ssid}"?')
        dialog.add_response("cancel", "Cancel")
        dialog.add_response("forget", "Forget")
        dialog.set_response_appearance("forget", Adw.ResponseAppearance.DESTRUCTIVE)

        def on_response(dialog, response):
            if response == "forget":
                self._perform_forget(item.ssid)
            dialog.destroy()

        dialog.connect("response", on_response)
        dialog.present()

    def _perform_forget(self, ssid):
        """Actually forget the network"""

        def forget_thread():
            try:
                # Get connection UUID first
                result = subprocess.run(
                    ["nmcli", "-t", "-f", "UUID,NAME", "connection", "show"],
                    capture_output=True,
                    text=True,
                )

                uuid = None
                for line in result.stdout.split("\n"):
                    if line and ssid in line:
                        uuid = line.split(":")[0]
                        break

                if uuid:
                    subprocess.run(
                        ["nmcli", "connection", "delete", uuid],
                        capture_output=True,
                        text=True,
                    )
                    GLib.idle_add(self._show_toast, f"Forgot network {ssid}")

            except Exception as e:
                print(f"Error forgetting network: {e}")

        thread = threading.Thread(target=forget_thread, daemon=True)
        thread.start()

    def _show_toast(self, message):
        """Show a toast notification"""
        toast = Adw.Toast.new(message)
        toast.set_timeout(3)

        # Find the toast overlay (create one if needed)
        if not hasattr(self, "_toast_overlay"):
            # Wrap existing content in toast overlay
            content = self.get_content()
            self.set_content(None)

            self._toast_overlay = Adw.ToastOverlay()
            self._toast_overlay.set_child(content)
            self.set_content(self._toast_overlay)

        self._toast_overlay.add_toast(toast)

    def _run_nmcli_command(self, args):
        """Run nmcli command in background"""

        def run_command():
            try:
                subprocess.run(["nmcli"] + args, capture_output=True, text=True)
            except Exception as e:
                print(f"Error running nmcli command: {e}")

        thread = threading.Thread(target=run_command, daemon=True)
        thread.start()

    def _refresh_networks(self):
        """Refresh the list of WiFi networks"""
        if not self._should_refresh:
            return GLib.SOURCE_REMOVE

        # Show loading state while refreshing
        self._show_loading()

        def get_networks():
            try:
                # Check if WiFi interface exists before scanning
                wifi_interface = self._get_wifi_interface()
                if wifi_interface is None:
                    GLib.idle_add(self._show_no_wifi_interface)
                    return

                # Run nmcli to get WiFi networks
                result = subprocess.run(
                    [
                        "nmcli",
                        "-t",
                        "-f",
                        "IN-USE,SSID,BSSID,MODE,CHAN,RATE,SIGNAL,BARS,SECURITY,ACTIVE",
                        "device",
                        "wifi",
                        "list",
                    ],
                    capture_output=True,
                    text=True,
                    timeout=15,
                )

                if result.returncode != 0:
                    GLib.idle_add(self._update_network_list, [])
                    return

                networks = []
                lines = result.stdout.strip().split("\n")

                for line in lines:
                    if not line.strip():
                        continue

                    # Parse the colon-separated output
                    # Handle escaped colons in BSSID field properly
                    fields = []
                    current_field = ""
                    i = 0
                    while i < len(line):
                        if line[i] == '\\' and i + 1 < len(line) and line[i + 1] == ':':
                            # Escaped colon, add to current field
                            current_field += line[i:i+2]
                            i += 2
                        elif line[i] == ':':
                            # Field separator
                            fields.append(current_field)
                            current_field = ""
                            i += 1
                        else:
                            current_field += line[i]
                            i += 1
                    # Add the last field
                    if current_field:
                        fields.append(current_field)

                    if len(fields) >= 10:
                        network_data = {
                            "IN-USE": fields[0],
                            "SSID": fields[1],
                            "BSSID": fields[2],
                            "MODE": fields[3],
                            "CHAN": fields[4],
                            "RATE": fields[5],
                            "SIGNAL": fields[6],
                            "BARS": fields[7],
                            "SECURITY": fields[8],
                            "ACTIVE": fields[9],
                        }

                        # Skip empty SSIDs (hidden networks without names)
                        if network_data["SSID"].strip():
                            networks.append(WiFiNetwork(network_data))

                # Sort by connection status first (in_use, then active), then by signal strength
                networks.sort(key=lambda n: (not n.in_use, not n.active, -n.signal))

                GLib.idle_add(self._update_network_list, networks)

            except subprocess.TimeoutExpired:
                print("Network scan timeout")
                GLib.idle_add(self._update_network_list, [])
            except Exception as e:
                print(f"Error refreshing networks: {e}")
                GLib.idle_add(self._update_network_list, [])

        if self._refresh_thread and self._refresh_thread.is_alive():
            return GLib.SOURCE_CONTINUE

        self._refresh_thread = threading.Thread(target=get_networks, daemon=True)
        self._refresh_thread.start()
        return GLib.SOURCE_CONTINUE

    def _update_network_list(self, networks):
        """Update the network list in the UI"""
        self._current_networks = networks
        current_query = self.get_search_text()

        if current_query.strip():
            self.on_search_changed(current_query)
        else:
            self.on_search_cleared()

        return GLib.SOURCE_REMOVE

    def _update_ui(self):
        """Update the UI with filtered networks"""
        if not self._filtered_networks:
            self.remove_all_items()
            self._show_empty("No Networks Found", "No WiFi networks match your search.")
            return

        # Store selected network
        selected_bssid = None
        selected_position = self._selection_model.get_selected()
        if selected_position != Gtk.INVALID_LIST_POSITION:
            selected_item = self._item_store.get_item(selected_position)
            if selected_item:
                selected_bssid = selected_item.bssid

        # Update the list
        self.remove_all_items()
        for network in self._filtered_networks:
            self.add_item(network)

        self._show_results()

        # Restore selection
        if selected_bssid:
            self._restore_selection(selected_bssid)

    def _restore_selection(self, selected_bssid):
        """Restore selection by BSSID"""
        for i in range(self._item_store.get_n_items()):
            item = self._item_store.get_item(i)
            if item.bssid == selected_bssid:
                self._selection_model.set_selected(i)
                return True
        return False

    def on_close_request(self):
        self._should_refresh = False
        return False

    def _get_wifi_interface(self):
        """Get the active WiFi interface name, returns None if not found"""
        try:
            # Get all WiFi devices
            result = subprocess.run(
                ["nmcli", "-t", "-f", "DEVICE,TYPE,STATE", "device", "status"],
                capture_output=True,
                text=True,
                timeout=5,
            )

            if result.returncode == 0:
                for line in result.stdout.strip().split("\n"):
                    if line:
                        parts = line.split(":")
                        if len(parts) >= 3:
                            device, device_type, state = parts[0], parts[1], parts[2]
                            # Look for WiFi devices that are connected or available
                            if device_type == "wifi" and state in [
                                "connected",
                                "disconnected",
                                "unavailable",
                            ]:
                                return device

            # Try common WiFi interface names
            common_names = ["wlan0", "wlp0s20f3", "wlo1", "wifi0"]
            for name in common_names:
                try:
                    check_result = subprocess.run(
                        ["nmcli", "device", "show", name],
                        capture_output=True,
                        text=True,
                        timeout=2,
                    )
                    if check_result.returncode == 0:
                        return name
                except subprocess.TimeoutExpired:
                    continue

        except (subprocess.TimeoutExpired, Exception):
            pass

        # No WiFi interface found
        return None

    def _show_wifi_interface_error(self, action):
        """Show error when no WiFi interface is found"""
        error_dialog = Adw.MessageDialog.new(self, "No WiFi Interface Found")
        error_dialog.set_body(
            f"No WiFi interface could be detected on this system.\n\n"
            f"Cannot {action} without a WiFi interface. Please ensure:\n"
            f"• WiFi hardware is available\n"
            f"• NetworkManager is running\n"
            f"• WiFi drivers are installed"
        )
        error_dialog.add_response("ok", "OK")
        error_dialog.present()

    def _show_no_wifi_interface(self):
        """Show empty state when no WiFi interface is available"""
        self._show_empty(
            "No WiFi Interface Available",
            "No WiFi interface could be detected on this system.\n\n"
            "Please ensure WiFi hardware is available and NetworkManager is running.",
        )


class WirelessNetworksApplication(Adw.Application):

    def __init__(self):
        super().__init__(application_id=APP_ID, flags=Gio.ApplicationFlags.FLAGS_NONE)

    def do_activate(self):
        win = self.props.active_window
        if not win:
            win = WirelessNetworksWindow(application=self)
        win.present()

    def do_startup(self):
        Adw.Application.do_startup(self)


def main():
    app = WirelessNetworksApplication()
    return app.run(sys.argv)


if __name__ == "__main__":
    main()
