{
  pkgs,
  lib,
  ...
}: let
  pkg = pkgs.python3Packages.buildPythonApplication {
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

    preFixup = ''
      gappsWrapperArgs+=(--prefix PYTHONPATH : "${pkgs.python3.withPackages (p: [
        p.pygobject3
      ])}/${pkgs.python3.sitePackages}")
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
  };
in
  pkgs.symlinkJoin {
    name = "scratchpad";
    paths = [
      pkg
      (pkgs.makeDesktopItem {
        name = "scratchpad";
        desktopName = "Scratchpad";
        exec = lib.getExe pkg;
        icon = "${pkg}/share/pixmaps/net.knoopx.scratchpad.png";
      })
    ];
  }
