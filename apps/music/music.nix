{
  pkgs,
  lib,
  ...
}: let
  pkg = pkgs.python3Packages.buildPythonApplication {
    name = "music";
    src = ./.;
    pyproject = false;

    nativeBuildInputs = with pkgs; [
      wrapGAppsHook4
      gobject-introspection
      glib
    ];

    buildInputs = with pkgs;
      [
        libadwaita
      ]
      ++ (with pkgs.gst_all_1; [
        gstreamer
        gst-plugins-base
        gst-plugins-good
        gst-plugins-bad
        gst-plugins-ugly
      ]);

    propagatedBuildInputs = with pkgs.python3Packages; [
      pygobject3
      orjson
    ];

    installPhase = ''
      runHook preInstall

      mkdir -p $out/bin $out/${pkgs.python3.sitePackages} $out/share/glib-2.0/schemas $out/share/pixmaps

      # Install local Python modules
      cp *.py $out/${pkgs.python3.sitePackages}/

      # Install shared Python modules from parent directory
      cp ${../picker_window.py} $out/${pkgs.python3.sitePackages}/picker_window.py
      cp ${../context_menu_window.py} $out/${pkgs.python3.sitePackages}/context_menu_window.py
      cp ${../star_button.py} $out/${pkgs.python3.sitePackages}/star_button.py
      cp ${../circular_progress.py} $out/${pkgs.python3.sitePackages}/circular_progress.py
      cp ${../badge.py} $out/${pkgs.python3.sitePackages}/badge.py

      # Install main executable
      cp music.py $out/bin/music
      chmod +x $out/bin/music

      # Install icon
      cp icon.png $out/share/pixmaps/net.knoopx.music.png

      # Install GSettings schema
      install -Dm644 net.knoopx.music.gschema.xml $out/share/glib-2.0/schemas/
      glib-compile-schemas $out/share/glib-2.0/schemas/

      runHook postInstall
    '';

    meta.mainProgram = "music";
  };
in
  pkgs.symlinkJoin {
    name = "music";
    paths = [
      pkg
      (pkgs.makeDesktopItem {
        name = "music";
        desktopName = "Music";
        exec = lib.getExe pkg;
        icon = "${pkg}/share/pixmaps/net.knoopx.music.png";
      })
    ];
  }
