{pkgs, ...}:
pkgs.python313Packages.buildPythonApplication {
  name = "file-picker";
  src = pkgs.runCommand "file-picker-src" {} ''
    mkdir -p $out
    cp -r ${./.}/* $out/
  '';
  pyproject = false;

  nativeBuildInputs = with pkgs; [
    wrapGAppsHook4
    copyDesktopItems
    gobject-introspection
    glib # for glib-compile-schemas
  ];

  buildInputs = with pkgs; [
    libadwaita
    gtk4
    glib-networking
    pkgs.python313Packages.pygobject3
  ];

  desktopItems = [
    (pkgs.makeDesktopItem {
      name = "file-picker";
      desktopName = "File Picker";
      exec = "file-picker";
      icon = "net.knoopx.filepicker";
    })
  ];

  buildPhase = ''
    mkdir -p $out/{bin,share/file-picker,share/pixmaps}
    cp -r ./* $out/share/file-picker/
    chmod +x $out/share/file-picker/file-picker.py
    ln -s $out/share/file-picker/file-picker.py $out/bin/file-picker
    cp icon.png $out/share/pixmaps/net.knoopx.filepicker.png
  '';

  preFixup = ''
    gappsWrapperArgs+=(--prefix PYTHONPATH : "${pkgs.python313.withPackages (p: [p.pygobject3])}/${pkgs.python313.sitePackages}")
  '';

  meta.mainProgram = "file-picker";
}
