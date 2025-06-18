{pkgs, ...}:
pkgs.python3Packages.buildPythonApplication {
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
    gappsWrapperArgs+=(--prefix PYTHONPATH : "${pkgs.python3.withPackages (p: [
      p.pygobject3
    ])}/${pkgs.python3.sitePackages}")
  '';

  buildPhase = ''
    mkdir -p $out/bin $out/share/pixmaps
    install -m 755 -D launcher.py $out/bin/launcher
    cp icon.png $out/share/pixmaps/net.knoopx.launcher.png
  '';

  meta.mainProgram = "launcher";
}
