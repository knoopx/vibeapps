{pkgs, ...}:
pkgs.python313Packages.buildPythonApplication {
  name = "image-picker";
  src = pkgs.runCommand "image-picker-src" {} ''
    mkdir -p $out
    cp -r ${./.}/* $out/
  '';
  pyproject = false;

  nativeBuildInputs = with pkgs; [
    wrapGAppsHook4
    copyDesktopItems
    gobject-introspection
    glib # for glib-compile-schemas
    libadwaita
    gtk4
  ];

  buildInputs = with pkgs; [
    libadwaita
    gtk4
    glib-networking
    pkgs.python313Packages.pygobject3
    gobject-introspection
  ];

  desktopItems = [
    (pkgs.makeDesktopItem {
      name = "image-picker";
      desktopName = "Image Picker";
      exec = "image-picker";
      icon = "net.knoopx.imagepicker";
    })
  ];

  buildPhase = ''
    mkdir -p $out/{bin,share/image-picker,share/pixmaps}
    cp -r ./* $out/share/image-picker/
    chmod +x $out/share/image-picker/image-picker.py
    ln -s $out/share/image-picker/image-picker.py $out/bin/image-picker
    cp icon.png $out/share/pixmaps/net.knoopx.imagepicker.png
  '';

  preFixup = ''
    gappsWrapperArgs+=(--prefix PYTHONPATH : "${pkgs.python313.withPackages (p: [p.pygobject3])}/${pkgs.python313.sitePackages}")
  '';

  meta.mainProgram = "image-picker";
}
