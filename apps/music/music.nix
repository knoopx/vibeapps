{
  pkgs,
  lib,
  ...
}: let
  pkg = pkgs.python3Packages.buildPythonApplication {
    name = "music";
    src = pkgs.runCommand "music-src" {} ''
      mkdir -p $out
      cp ${./music.py} $out/music.py
      cp ${../picker_window.py} $out/picker_window.py
      cp ${../context_menu_window.py} $out/context_menu_window.py
      cp ${../star_button.py} $out/star_button.py
    '';
    pyproject = false;

    nativeBuildInputs = with pkgs; [
      wrapGAppsHook4
      gobject-introspection
    ];

    buildInputs = with pkgs; [
      libadwaita
      pkgs.gst_all_1.gstreamer
      pkgs.gst_all_1.gst-plugins-base
      pkgs.gst_all_1.gst-plugins-good
      pkgs.gst_all_1.gst-plugins-bad
      pkgs.gst_all_1.gst-plugins-ugly
    ];

    preFixup = ''
      gappsWrapperArgs+=(--prefix PYTHONPATH : "${pkgs.python3.withPackages (p: [
        p.pygobject3
        p.orjson
      ])}/${pkgs.python3.sitePackages}")
    '';

    buildPhase = ''
      mkdir -p $out/bin $out/lib/python
      cp $src/picker_window.py $out/lib/python/
      cp $src/context_menu_window.py $out/lib/python/
      cp $src/star_button.py $out/lib/python/
      cp $src/music.py $out/bin/music
      chmod +x $out/bin/music
    '';

    postFixup = ''
      # Ensure picker_window.py is in the Python path
      wrapProgram $out/bin/music \
        --prefix PYTHONPATH : $out/lib/python
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
        icon = "multimedia-player-symbolic";
      })
    ];
  }
