{pkgs, ...}:
pkgs.python313Packages.buildPythonApplication {
  name = "launcher";
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
    install -m 755 -D launcher.py $out/bin/launcher
    cp icon.png $out/share/pixmaps/net.knoopx.launcher.png
  '';

  meta.mainProgram = "launcher";
}
