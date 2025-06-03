{
  pkgs,
  lib,
  ...
}: let
  pkg = pkgs.python3Packages.buildPythonApplication {
    name = "windows";
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
      mkdir -p $out/bin $out/lib/python
      cp windows.py $out/bin/windows
      cp ${../picker_window.py} $out/lib/python/picker_window.py
      cp ${../context_menu_window.py} $out/lib/python/context_menu_window.py
      chmod +x $out/bin/windows
    '';

    preFixup = ''
      gappsWrapperArgs+=(
        --prefix PYTHONPATH : "$out/lib/python:${pkgs.python3.withPackages (p: [
        p.pygobject3
      ])}/${pkgs.python3.sitePackages}"
      )
    '';

    meta.mainProgram = "windows";
  };
in
  pkgs.symlinkJoin {
    name = "windows";
    paths = [
      pkg
      (pkgs.makeDesktopItem {
        name = "windows";
        desktopName = "Windows";
        exec = lib.getExe pkg;
        icon = "view-grid-symbolic";
      })
    ];
  }
