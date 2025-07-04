{
  pkgs,
  lib,
  ...
}:
pkgs.python313Packages.buildPythonApplication {
  name = "dataset-viewer";
  src = ./.;
  pyproject = false;

  nativeBuildInputs = with pkgs; [
    wrapGAppsHook4
    copyDesktopItems
    gobject-introspection
  ];

  buildInputs = with pkgs; [
    libadwaita
  ];

  preFixup = ''
    gappsWrapperArgs+=(--prefix PYTHONPATH : "${pkgs.python313.withPackages (p: [
      p.pygobject3
    ])}/${pkgs.python313.sitePackages}")
  '';

  buildPhase = ''
    mkdir -p $out/bin $out/share/pixmaps
    install -m 755 -D dataset-viewer.py $out/bin/ds
    cp icon.png $out/share/pixmaps/net.knoopx.dataset-viewer.png
  '';

  meta.mainProgram = "ds";
}
