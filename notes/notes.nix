{
  pkgs,
  lib,
  ...
}: let
  md2html = pkgs.callPackage ../md2html/md2html.nix {};

  pkg = pkgs.python3Packages.buildPythonApplication {
    name = "notes";
    src = ./.;
    dontUnpack = true;
    pyproject = false;

    nativeBuildInputs = with pkgs; [
      wrapGAppsHook4
      gobject-introspection
    ];

    buildInputs = with pkgs; [
      libadwaita
      gtksourceview5
      webkitgtk_6_0
      glib-networking
    ];

    preFixup = ''
      gappsWrapperArgs+=(--prefix PATH : "${md2html}/bin" --prefix PYTHONPATH : "${pkgs.python3.withPackages (p: [
        p.pygobject3
      ])}/${pkgs.python3.sitePackages}")
    '';

    buildPhase = ''
      mkdir -p $out/{bin,share}
      cp -r $src $out/share/notes
      chmod +x $out/share/notes/notes.py
      ln -s $out/share/notes/notes.py $out/bin/notes
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
