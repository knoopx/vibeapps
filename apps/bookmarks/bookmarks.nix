{
  pkgs,
  lib,
  ...
}: let
  pkg = pkgs.python3Packages.buildPythonApplication {
    name = "bookmarks";
    src = ./.;
    pyproject = false;

    nativeBuildInputs = with pkgs; [
      wrapGAppsHook4
      gobject-introspection
    ];

    buildInputs = with pkgs; [
      libadwaita
    ];

    propagatedBuildInputs = with pkgs.python3Packages; [
      pygobject3
    ];

    installPhase = ''
      runHook preInstall

      mkdir -p $out/bin $out/${pkgs.python3.sitePackages}/ $out/share/pixmaps/

      cp *.py $out/${pkgs.python3.sitePackages}/
      cp ${../picker_window.py} $out/${pkgs.python3.sitePackages}/picker_window.py
      cp ${../context_menu_window.py} $out/${pkgs.python3.sitePackages}/context_menu_window.py

      cp $src/bookmarks.py $out/bin/bookmarks
      chmod +x $out/bin/bookmarks

      cp $src/icon.png $out/share/pixmaps/net.knoopx.bookmarks.png

      runHook postInstall
    '';

    meta.mainProgram = "bookmarks";
  };
in
  pkgs.symlinkJoin {
    name = "bookmarks";
    paths = [
      pkg
      (pkgs.makeDesktopItem {
        name = "bookmarks";
        desktopName = "Bookmarks";
        exec = lib.getExe pkg;
        icon = "${pkg}/share/pixmaps/net.knoopx.bookmarks.png";
      })
    ];
  }
