{pkgs, ...}:
pkgs.python313Packages.buildPythonApplication {
  name = "webkit-shell";
  src = ./.;
  pyproject = false;

  nativeBuildInputs = with pkgs; [
    wrapGAppsHook4
    copyDesktopItems
    gobject-introspection
  ];

  buildInputs = with pkgs; [
    libadwaita
    gtksourceview5
    webkitgtk_6_0
    glib-networking
  ];

  desktopItems = [
    (pkgs.makeDesktopItem {
      name = "webkit-shell";
      desktopName = "WebKit Shell";
      exec = "webkit-shell";
      icon = "net.knoopx.webkit-shell";
    })
  ];

  preFixup = ''
    gappsWrapperArgs+=(--prefix PYTHONPATH : "${pkgs.python313.withPackages (p: [
      p.pygobject3
    ])}/${pkgs.python313.sitePackages}")
  '';

  buildPhase = ''
    mkdir -p $out/bin $out/share/pixmaps
    install -m 755 -D webkit-shell.py $out/bin/webkit-shell
    cp icon.png $out/share/pixmaps/net.knoopx.webkit-shell.png
  '';

  meta.mainProgram = "webkit-shell";
}
