{pkgs, ...}:
pkgs.python312Packages.buildPythonApplication {
  name = "scratchpad";
  src = ./.;
  pyproject = false;

  nativeBuildInputs = with pkgs; [
    wrapGAppsHook4
    gobject-introspection
  ];

  buildInputs = with pkgs; [
    libadwaita
    # Add other GTK or system dependencies here if needed
  ];

  desktopItems = [
    (pkgs.makeDesktopItem {
      name = "scratchpad";
      desktopName = "Scratchpad";
      exec = "scratchpad";
      icon = "net.knoopx.scratchpad";
    })
  ];

  preFixup = ''
    gappsWrapperArgs+=(--prefix PYTHONPATH : "${pkgs.python312.withPackages (p: [
      p.pygobject3
    ])}/${pkgs.python312.sitePackages}")
  '';

  buildPhase = ''
    mkdir -p $out/bin $out/share/pixmaps
    install -m 755 -D scratchpad.py $out/bin/scratchpad
    cp icon.png $out/share/pixmaps/net.knoopx.scratchpad.png
  '';

  meta = {
    description = "An interactive scratchpad calculator";
    mainProgram = "scratchpad";
  };
}
