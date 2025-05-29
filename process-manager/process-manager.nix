{
  pkgs,
  lib,
  ...
}: let
  pkg = pkgs.python3Packages.buildPythonApplication {
    name = "process-manager";
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
      cp process-manager.py $out/bin/process-manager
      cp ${../picker_window.py} $out/lib/python/picker_window.py
      cp ${../context_menu_window.py} $out/lib/python/context_menu_window.py
      chmod +x $out/bin/process-manager
    '';

    preFixup = ''
      gappsWrapperArgs+=(
        --prefix PYTHONPATH : "$out/lib/python:${pkgs.python3.withPackages (p: [
        p.pygobject3
        p.psutil
      ])}/${pkgs.python3.sitePackages}"
      )
    '';

    meta.mainProgram = "process-manager";
  };
in
  pkgs.symlinkJoin {
    name = "process-manager";
    paths = [
      pkg
      (pkgs.makeDesktopItem {
        name = "process-manager";
        desktopName = "Process Manager";
        exec = lib.getExe pkg;
        icon = "find-location-symbolic";
      })
    ];
  }
