{pkgs, ...}:
pkgs.python313Packages.buildPythonApplication {
  name = "music";
  src = ./.;
  pyproject = false;

  nativeBuildInputs = with pkgs; [
    wrapGAppsHook4
    copyDesktopItems
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

  propagatedBuildInputs = with pkgs.python313Packages; [
    pygobject3
    orjson
  ];

  desktopItems = [
    (pkgs.makeDesktopItem {
      name = "music";
      desktopName = "Music";
      exec = "music";
      icon = "net.knoopx.music";
    })
  ];

  installPhase = ''
    runHook preInstall

    mkdir -p $out/bin $out/${pkgs.python313.sitePackages} $out/share/glib-2.0/schemas $out/share/pixmaps

    # Install local Python modules
    cp *.py $out/${pkgs.python313.sitePackages}/

    # Install shared Python modules from parent directory
    cp ${../picker_window.py} $out/${pkgs.python313.sitePackages}/picker_window.py
    cp ${../context_menu_window.py} $out/${pkgs.python313.sitePackages}/context_menu_window.py
    cp ${../star_button.py} $out/${pkgs.python313.sitePackages}/star_button.py
    cp ${../circular_progress.py} $out/${pkgs.python313.sitePackages}/circular_progress.py
    cp ${../badge.py} $out/${pkgs.python313.sitePackages}/badge.py

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
}
