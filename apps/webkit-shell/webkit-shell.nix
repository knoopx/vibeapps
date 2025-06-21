{
  pkgs,
  lib,
  ...
}: let
  pkg = pkgs.python312Packages.buildPythonApplication {
    name = "webkit-shell";
    src = ./.;
    pyproject = false;

    nativeBuildInputs = with pkgs; [
      wrapGAppsHook4
      gobject-introspection
    ];

    buildInputs = with pkgs; [
      libadwaita
      gtksourceview5
      webkitgtk_6_0
      glib-networking
    ];

    preFixup = ''
      gappsWrapperArgs+=(--prefix PYTHONPATH : "${pkgs.python3.withPackages (p: [
        p.pygobject3
      ])}/${pkgs.python3.sitePackages}")
    '';

    buildPhase = ''
      mkdir -p $out/bin $out/share/pixmaps
      install -m 755 -D webkit-shell.py $out/bin/webkit-shell
      cp icon.png $out/share/pixmaps/net.knoopx.webkit-shell.png
    '';

    meta.mainProgram = "webkit-shell";
  };
in
  pkgs.symlinkJoin {
    name = "webkit-shell";
    paths = [
      pkg
      (pkgs.makeDesktopItem {
        name = "webkit-shell";
        desktopName = "WebKit Shell";
        exec = lib.getExe pkg;
        icon = "${pkg}/share/pixmaps/net.knoopx.webkit-shell.png";
      })
    ];
  }
