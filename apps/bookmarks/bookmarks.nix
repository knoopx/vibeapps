{pkgs, ...}:
pkgs.python313Packages.buildPythonApplication {
  name = "bookmarks";
  src = ./.;
  pyproject = false;

  nativeBuildInputs = with pkgs; [
    wrapGAppsHook4
    copyDesktopItems
    gobject-introspection
  ];

  buildInputs = with pkgs; [
    libadwaita
    webkitgtk_6_0
    glib-networking
  ];

  propagatedBuildInputs = with pkgs.python313Packages; [
    pygobject3
  ];

  desktopItems = [
    (pkgs.makeDesktopItem {
      name = "bookmarks";
      desktopName = "Bookmarks";
      exec = "bookmarks";
      icon = "net.knoopx.bookmarks";
    })
  ];

  installPhase = ''
    runHook preInstall

    mkdir -p $out/bin $out/${pkgs.python313.sitePackages}/ $out/share/pixmaps/

    cp *.py $out/${pkgs.python313.sitePackages}/
    cp ${../picker_window.py} $out/${pkgs.python313.sitePackages}/picker_window.py
    cp ${../picker_window_with_preview.py} $out/${pkgs.python313.sitePackages}/picker_window_with_preview.py
    cp ${../context_menu_window.py} $out/${pkgs.python313.sitePackages}/context_menu_window.py

    cp $src/bookmarks.py $out/bin/bookmarks
    chmod +x $out/bin/bookmarks

    cp $src/icon.png $out/share/pixmaps/net.knoopx.bookmarks.png

    runHook postInstall
  '';

  meta.mainProgram = "bookmarks";
}
