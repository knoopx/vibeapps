{
  pkgs,
  lib,
  ...
}: let
  pkg = pkgs.python312Packages.buildPythonApplication {
    name = "wireless-networks";
    src = ./.;
    pyproject = false;

    nativeBuildInputs = with pkgs; [
      wrapGAppsHook4
      gobject-introspection
    ];

    buildInputs = with pkgs; [
      libadwaita
    ];

    propagatedBuildInputs = with pkgs.python312Packages; [
      pygobject3
    ];

    installPhase = ''
      runHook preInstall

      mkdir -p $out/bin $out/${pkgs.python312.sitePackages}/ $out/share/pixmaps/

      cp *.py $out/${pkgs.python312.sitePackages}/
      cp ${../picker_window.py} $out/${pkgs.python312.sitePackages}/picker_window.py
      cp ${../context_menu_window.py} $out/${pkgs.python312.sitePackages}/context_menu_window.py

      cp $src/wireless-networks.py $out/bin/wireless-networks
      chmod +x $out/bin/wireless-networks

      cp $src/icon.png $out/share/pixmaps/net.knoopx.wireless.png

      runHook postInstall
    '';

    meta.mainProgram = "wireless-networks";
  };
in
  pkgs.symlinkJoin {
    name = "wireless-networks";
    paths = [
      pkg
      (pkgs.makeDesktopItem {
        name = "wireless-networks";
        desktopName = "Wireless Networks";
        exec = lib.getExe pkg;
        icon = "${pkg}/share/pixmaps/net.knoopx.wireless.png";
      })
    ];
  }
