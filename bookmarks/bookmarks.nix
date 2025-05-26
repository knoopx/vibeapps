{
  pkgs,
  lib,
  ...
}: let
  pkg = pkgs.python3Packages.buildPythonApplication {
    name = "bookmarks";
    src = pkgs.runCommand "bookmarks-src" {} ''
      mkdir -p $out
      cp ${./bookmarks.py} $out/bookmarks.py
      cp ${../picker_window.py} $out/picker_window.py
    '';
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
      mkdir -p $out/bin $out/lib/python
      cp $src/picker_window.py $out/lib/python/
      cp $src/bookmarks.py $out/bin/bookmarks
      chmod +x $out/bin/bookmarks
    '';

    postFixup = ''
      # Ensure picker_window.py is in the Python path
      wrapProgram $out/bin/bookmarks \
        --prefix PYTHONPATH : $out/lib/python
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
