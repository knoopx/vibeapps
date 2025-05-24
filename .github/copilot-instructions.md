# LLM Agent Instructions

## VSCode Terminal (Fish Shell) Limitations

The VSCode terminal uses **Fish**, which doesn't support multi-line `python -c` commands like:

```bash
python -c "
print('Hello')
"
````

Use one of:

* Single-line commands
* An interactive REPL
* A temp script file

## System Overview

* **OS**: NixOS 25.11 (Xantusia)
* **CPU**: i7-11700K (8C/16T)
* **RAM**: 32GB
* **Shell**: Fish 4.0.2
* **DE**: niri (Wayland)
* **Kernel**: Linux 6.14.7-zen1
* **Python**: 3.12.10
* **JS Runtime**: Bun 1.2.14
* **Pkg Mgr**: Nix 2.28.3

## Repository Contents

### Python (GTK4/libadwaita)

* `chat`: OpenAI chat UI
* `ds`: Image-caption dataset viewer
* `launcher`: Fast fuzzy launcher
* `music`: Album browser/player
* `notes`: Markdown editor with wiki-links
* `nix-packages`: Nix pkg search
* `scratchpad`: Calculator (Soulver-like)
* `webkit-shell`: WebView shell
* `reminder`: Calendar entry UI
* `mdx-editor`: Markdown + React editor

### JavaScript

* `md2html`: Markdown to HTML converter
* `remarkDefinitionList`: Remark plugin

### System Tools

* `raise-or-open-url`: URL/window switcher (Firefox + brotab + niri)

## Architecture

* All apps built/reproducible via Nix (`flake.nix`)
* GTK4/libadwaita UI, WebKit for embedded views
* Designed for Wayland (niri)

## Running Apps

Python:

```bash
nix --offline run path:.#app_name -- args
```

JavaScript:

```bash
bun run md2html/md2html.js
```

## Testing

Python:

```bash
cd app && python -m unittest test_*.py
```

JavaScript:

```bash
bun test
```