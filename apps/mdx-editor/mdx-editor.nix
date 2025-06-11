{
  pkgs,
  lib,
  ...
}: let
  deps = pkgs.stdenv.mkDerivation {
    name = "mdx-editor-deps";
    dontUnpack = true;
    nativeBuildInputs = with pkgs; [
      bun
    ];

    outputHashAlgo = "sha256";
    outputHashMode = "recursive";
    outputHash = "sha256-70EwmwlqsKI5/RMxD54gyVW63NTNC5tKss9le3XDcuc=";

    buildPhase = ''
      bun add vite react react-dom @mdxeditor/editor
      mv node_modules $out
    '';
  };

  assets = pkgs.stdenv.mkDerivation {
    name = "mdx-editor-assets";
    src = ./template;
    nativeBuildInputs = with pkgs; [
      bun
    ];

    outputHashAlgo = "sha256";
    outputHashMode = "recursive";
    outputHash = "sha256-6UB5o1L2a3utfFwmDejzmyThRPrU/5OarPHxnT+em48=";

    buildPhase = ''
      cp -r ${deps} node_modules
      bun node_modules/vite/bin/vite.js build
      mv dist $out
    '';
  };

  pkg = pkgs.python3Packages.buildPythonApplication {
    name = "mdx-editor";
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
      gappsWrapperArgs+=(--prefix PYTHONPATH : "${pkgs.python3.withPackages (p: [
        p.pygobject3
      ])}/${pkgs.python3.sitePackages}")
    '';

    buildPhase = ''
      mkdir -p $out/bin $out/share/pixmaps
      install -m 755 -D mdx-editor.py $out/bin/mdx-editor
      cp -r ${assets}/* $out/bin/
      substituteInPlace $out/bin/index.html --replace-fail "/assets/" "./assets/"
      cp icon.png $out/share/pixmaps/net.knoopx.mdx-editor.png
    '';

    meta.mainProgram = "mdx-editor";
  };
in
  pkgs.symlinkJoin {
    name = "mdx-editor";
    paths = [
      pkg
      (pkgs.makeDesktopItem {
        name = "mdx-editor";
        desktopName = "Notes";
        exec = lib.getExe pkg;
        icon = "${pkg}/share/pixmaps/net.knoopx.mdx-editor.png";
      })
    ];
  }
