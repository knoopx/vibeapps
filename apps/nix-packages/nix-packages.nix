{
  pkgs,
  lib,
  ...
}: let
  pkg = pkgs.python3Packages.buildPythonApplication {
    name = "nix-packages";
    src = ./.;
    pyproject = false;

    nativeBuildInputs = with pkgs; [
      wrapGAppsHook4
      gobject-introspection
    ];

    buildInputs = with pkgs; [
      libadwaita
    ];

    buildPhase = ''
      mkdir -p $out/bin $out/lib/python $out/share/pixmaps
      cp nix-packages.py $out/bin/nix-packages
      cp ${../picker_window.py} $out/lib/python/picker_window.py
      cp ${../context_menu_window.py} $out/lib/python/context_menu_window.py
      cp $src/icon.png $out/share/pixmaps/net.knoopx.nix-packages.png
      chmod +x $out/bin/nix-packages
    '';

    preFixup = ''
      gappsWrapperArgs+=(
        --prefix PYTHONPATH : "$out/lib/python:${pkgs.python3.withPackages (p: [
        p.pygobject3
        p.requests
      ])}/${pkgs.python3.sitePackages}"
      )
    '';

    meta.mainProgram = "nix-packages";
  };
in
  pkgs.symlinkJoin {
    name = "nix-packages";
    paths = [
      pkg
      (pkgs.makeDesktopItem {
        name = "nix-packages";
        desktopName = "Nix Packages";
        exec = lib.getExe pkg;
        icon = "${pkg}/share/pixmaps/net.knoopx.nix-packages.png";
      })
    ];
  }
