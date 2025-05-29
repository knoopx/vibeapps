{
  pkgs,
  lib,
  ...
}: let
  md2html = pkgs.callPackage ../md2html/md2html.nix {};

  pkg = pkgs.python3Packages.buildPythonApplication {
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

    buildPhase = ''
      mkdir -p $out/{bin,share/notes}
      cp -r ./* $out/share/notes/
      chmod +x $out/share/notes/notes.py
      ln -s $out/share/notes/notes.py $out/bin/notes
    '';

    postInstall = ''
      # Install schema
      mkdir -p $out/share/glib-2.0/schemas
      install -Dm644 ${./net.knoopx.notes.gschema.xml} $out/share/glib-2.0/schemas/net.knoopx.notes.gschema.xml
      glib-compile-schemas $out/share/glib-2.0/schemas/
    '';

    preFixup = ''
      gappsWrapperArgs+=(--prefix PATH : "${md2html}/bin" --prefix PYTHONPATH : "${pkgs.python3.withPackages (p: [
        p.pygobject3
      ])}/${pkgs.python3.sitePackages}")
    '';

    meta.mainProgram = "notes";
  };
in
  pkgs.symlinkJoin {
    name = "notes";
    paths = [
      pkg
      (pkgs.makeDesktopItem {
        name = "notes";
        desktopName = "Notes";
        exec = lib.getExe pkg;
        icon = "document-new-symbolic";
      })
    ];
  }
