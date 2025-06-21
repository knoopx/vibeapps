{pkgs, ...}: let
  md2html = pkgs.callPackage ../../utils/md2html/md2html.nix {};
in
  pkgs.python312Packages.buildPythonApplication {
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

    desktopItems = [
      (pkgs.makeDesktopItem {
        name = "chat";
        desktopName = "Chat";
        exec = "chat";
        icon = "net.knoopx.chat";
      })
    ];

    preFixup = ''
      gappsWrapperArgs+=(--prefix PATH : "${md2html}/bin" --prefix PYTHONPATH : "${pkgs.python312.withPackages (p: [
        p.pygobject3
        p.openai
      ])}/${pkgs.python312.sitePackages}")
    '';

    buildPhase = ''
      mkdir -p $out/bin $out/share/pixmaps
      install -m 755 -D chat.py $out/bin/chat
      cp icon.png $out/share/pixmaps/net.knoopx.chat.png
    '';

    meta.mainProgram = "chat";
  }
