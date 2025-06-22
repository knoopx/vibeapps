{pkgs, ...}:
pkgs.python313Packages.buildPythonApplication {
  name = "wireless-networks";
  src = ./.;
  pyproject = false;

  nativeBuildInputs = with pkgs; [
    wrapGAppsHook4
    gobject-introspection
  ];

  buildInputs = with pkgs; [
    libadwaita
  ];

  propagatedBuildInputs = with pkgs.python313Packages; [
    pygobject3
  ];

  desktopItems = [
    (pkgs.makeDesktopItem {
      name = "wireless-networks";
      desktopName = "Wireless Networks";
      exec = "wireless-networks";
      icon = "net.knoopx.wireless";
    })
  ];

  installPhase = ''
    runHook preInstall

    mkdir -p $out/bin $out/${pkgs.python313.sitePackages}/ $out/share/pixmaps/

    cp *.py $out/${pkgs.python313.sitePackages}/
    cp ${../picker_window.py} $out/${pkgs.python313.sitePackages}/picker_window.py
    cp ${../context_menu_window.py} $out/${pkgs.python313.sitePackages}/context_menu_window.py

    cp $src/wireless-networks.py $out/bin/wireless-networks
    chmod +x $out/bin/wireless-networks

    cp $src/icon.png $out/share/pixmaps/net.knoopx.wireless.png

    runHook postInstall
  '';

  meta.mainProgram = "wireless-networks";
}
