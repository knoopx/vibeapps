{pkgs, ...}: let
  md2html = pkgs.callPackage ../../utils/md2html/md2html.nix {};
in
  pkgs.python313Packages.buildPythonApplication {
    name = "notes";
    src = pkgs.runCommand "notes-src" {} ''
      mkdir -p $out
      cp -r ${./.}/* $out/
      cp ${../picker_window.py} $out/picker_window.py
      cp ${../context_menu_window.py} $out/context_menu_window.py
    '';
    pyproject = false;

    nativeBuildInputs = with pkgs; [
      wrapGAppsHook4
      gobject-introspection
      glib # for glib-compile-schemas
    ];

    buildInputs = with pkgs; [
      libadwaita
      gtksourceview5
      webkitgtk_6_0
      glib-networking
    ];

    desktopItems = [
      (pkgs.makeDesktopItem {
        name = "notes";
        desktopName = "Notes";
        exec = "notes";
        icon = "net.knoopx.notes";
      })
    ];

    buildPhase = ''
      mkdir -p $out/{bin,share/notes,share/pixmaps}
      cp -r ./* $out/share/notes/
      chmod +x $out/share/notes/notes.py
      ln -s $out/share/notes/notes.py $out/bin/notes
      cp icon.png $out/share/pixmaps/net.knoopx.notes.png
    '';

    postInstall = ''
      # Install schema
      mkdir -p $out/share/glib-2.0/schemas
      install -Dm644 ${./net.knoopx.notes.gschema.xml} $out/share/glib-2.0/schemas/net.knoopx.notes.gschema.xml
      glib-compile-schemas $out/share/glib-2.0/schemas/
    '';

    preFixup = ''
      gappsWrapperArgs+=(--prefix PATH : "${md2html}/bin" --prefix PYTHONPATH : "${pkgs.python313.withPackages (p: [
        p.pygobject3
      ])}/${pkgs.python313.sitePackages}")
    '';

    meta.mainProgram = "notes";
  }
