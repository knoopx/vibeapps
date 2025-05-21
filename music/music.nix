{
  pkgs,
  lib,
  ...
}: let
  pkg = pkgs.python3Packages.buildPythonApplication {
    name = "music";
    src = ./.;
    dontUnpack = true;
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
      ])}/${pkgs.python3.sitePackages}")
    '';

    buildPhase = ''
      mkdir -p $out/{bin,share}
      cp -r $src $out/share/music
      chmod +x $out/share/music/music.py
      ln -s $out/share/music/music.py $out/bin/music
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
