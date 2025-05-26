{
  pkgs,
  lib,
  ...
}: let
  pkg = pkgs.python3Packages.buildPythonApplication {
    name = "bookmarks";
    src = ./bookmarks.py;
    dontUnpack = true;
    pyproject = false;

    nativeBuildInputs = with pkgs; [
      wrapGAppsHook4
      gobject-introspection
    ];

    buildInputs = with pkgs; [
      libadwaita
    ];

    propagatedBuildInputs = with pkgs; [
      foxmarks
    ];

    preFixup = ''
      gappsWrapperArgs+=(--prefix PYTHONPATH : "${pkgs.python3.withPackages (p: [
        p.pygobject3
      ])}/${pkgs.python3.sitePackages}")
      gappsWrapperArgs+=(--prefix PATH : "${lib.makeBinPath [pkgs.foxmarks]}")
    '';

    buildPhase = ''
      install -m 755 -D $src $out/bin/bookmarks
    '';

    meta.mainProgram = "bookmarks";
  };
in
  pkgs.symlinkJoin {
    name = "bookmarks";
    paths = [
      pkg
      (pkgs.makeDesktopItem {
        name = "bookmarks";
        desktopName = "Bookmarks";
        exec = lib.getExe pkg;
        icon = "user-bookmarks-symbolic";
      })
    ];
  }
