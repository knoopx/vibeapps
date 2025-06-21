{
  pkgs,
  lib,
  ...
}:
pkgs.python312Packages.buildPythonApplication {
  name = "windows";
  src = ./.;
  pyproject = false;

  nativeBuildInputs = with pkgs; [
    wrapGAppsHook4
    gobject-introspection
  ];

  buildInputs = with pkgs; [
    libadwaita
  ];

  propagatedBuildInputs = with pkgs.python312Packages; [
    pygobject3
  ];

  desktopItems = [
    (pkgs.makeDesktopItem {
      name = "windows";
      desktopName = "Windows";
      exec = "windows";
      icon = "net.knoopx.windows";
    })
  ];

  installPhase = ''
    runHook preInstall

    mkdir -p $out/bin $out/share/net.knoopx.windows $out/share/pixmaps

    cp ${../picker_window.py} $out/share/net.knoopx.windows/picker_window.py
    cp ${../context_menu_window.py} $out/share/net.knoopx.windows/context_menu_window.py
    cp windows.py $out/share/net.knoopx.windows/windows.py

    # Create launcher wrapper script
    cat > $out/bin/windows << EOF
    #!/bin/sh
    export PYTHONPATH="$out/share/net.knoopx.windows:\$PYTHONPATH"
    exec ${pkgs.python312.withPackages (p: [p.pygobject3])}/bin/python $out/share/net.knoopx.windows/windows.py "\$@"
    EOF
    chmod +x $out/bin/windows

    # Install icon
    cp icon.png $out/share/pixmaps/net.knoopx.windows.png

    runHook postInstall
  '';

  meta.mainProgram = "windows";
}
