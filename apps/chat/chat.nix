{
  pkgs,
  lib,
  ...
}: let
  md2html = pkgs.callPackage ../../utils/md2html/md2html.nix {};

  pkg = pkgs.python312Packages.buildPythonApplication {
    name = "chat";
    src = ./.;
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
        p.openai
      ])}/${pkgs.python3.sitePackages}")
    '';

    buildPhase = ''
      mkdir -p $out/bin $out/share/pixmaps
      install -m 755 -D chat.py $out/bin/chat
      cp icon.png $out/share/pixmaps/net.knoopx.chat.png
    '';

    meta.mainProgram = "chat";
  };
in
  pkgs.symlinkJoin {
    name = "chat";
    paths = [
      pkg
      (pkgs.makeDesktopItem {
        name = "chat";
        desktopName = "Chat";
        exec = lib.getExe pkg;
        icon = "${pkg}/share/pixmaps/net.knoopx.chat.png";
      })
    ];
  }
