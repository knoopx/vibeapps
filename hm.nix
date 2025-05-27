{
  config,
  lib,
  pkgs,
  ...
}: let
  cfg = config.programs.vibeapps;

  # Call packages directly using callPackage
  vibeappsPackages = {
    bookmarks = pkgs.callPackage ./bookmarks/bookmarks.nix {};
    chat = pkgs.callPackage ./chat/chat.nix {};
    dataset-viewer = pkgs.callPackage ./dataset-viewer/dataset-viewer.nix {};
    launcher = pkgs.callPackage ./launcher/launcher.nix {};
    md2html = pkgs.callPackage ./md2html/md2html.nix {};
    music = pkgs.callPackage ./music/music.nix {};
    notes = pkgs.callPackage ./notes/notes.nix {};
    raise-or-open-url = pkgs.callPackage ./raise-or-open-url/raise-or-open-url.nix {};
    nix-packages = pkgs.callPackage ./nix-packages/nix-packages.nix {};
    scratchpad = pkgs.callPackage ./scratchpad/scratchpad.nix {};
  };

  # Define all available programs
  programNames = [
    "bookmarks"
    "chat"
    "dataset-viewer"
    "launcher"
    "md2html"
    "music"
    "notes"
    "raise-or-open-url"
    "nix-packages"
    "scratchpad"
  ];

  # Create options for each program
  programOptions = lib.genAttrs programNames (name: {
    enable = lib.mkEnableOption "Enable ${name}";
  });

  # Create packages list for enabled programs
  enabledPackages = lib.filter (pkg: pkg != null) (
    map (
      name:
        if cfg.${name}.enable
        then vibeappsPackages.${name}
        else null
    )
    programNames
  );
in {
  options.programs.vibeapps =
    programOptions
    // {
      enableAll = lib.mkOption {
        type = lib.types.bool;
        default = false;
        description = "Enable all vibeapps programs";
      };
    };

  config = lib.mkIf (cfg.enableAll || (lib.any (name: cfg.${name}.enable) programNames)) {
    home.packages =
      if cfg.enableAll
      then lib.attrValues vibeappsPackages
      else enabledPackages;

    # Activation script to kill launcher when enabled
    home.activation.kill-launcher = lib.mkIf (cfg.enableAll || cfg.launcher.enable) (
      lib.hm.dag.entryAfter ["writeBoundary"] ''
        $DRY_RUN_CMD ${pkgs.procps}/bin/pkill -f launcher || true
      ''
    );
  };
}
