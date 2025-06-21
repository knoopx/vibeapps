{pkgs, ...}:
pkgs.python312Packages.buildPythonApplication {
  name = "launcher";
  src = ./.;
  pyproject = false;

  nativeBuildInputs = with pkgs; [
    wrapGAppsHook4
    gobject-introspection
  ];

  buildInputs = with pkgs; [
    libadwaita
  ];

  preFixup = ''
    gappsWrapperArgs+=(--prefix PYTHONPATH : "${pkgs.python312.withPackages (p: [
      p.pygobject3
    ])}/${pkgs.python312.sitePackages}")
  '';

  buildPhase = ''
    mkdir -p $out/bin $out/share/pixmaps
    install -m 755 -D launcher.py $out/bin/launcher
    cp icon.png $out/share/pixmaps/net.knoopx.launcher.png
  '';

  meta.mainProgram = "launcher";
}
