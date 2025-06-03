{
  config,
  lib,
  pkgs,
  ...
}: let
  cfg = config.programs.vibeapps;

  # Call packages directly using callPackage
  vibeappsPackages = {
    bookmarks = pkgs.callPackage ./apps/bookmarks/bookmarks.nix {};
    chat = pkgs.callPackage ./apps/chat/chat.nix {};
    dataset-viewer = pkgs.callPackage ./apps/dataset-viewer/dataset-viewer.nix {};
    launcher = pkgs.callPackage ./apps/launcher/launcher.nix {};
    music = pkgs.callPackage ./apps/music/music.nix {};
    notes = pkgs.callPackage ./apps/notes/notes.nix {};
    process-manager = pkgs.callPackage ./apps/process-manager/process-manager.nix {};
    nix-packages = pkgs.callPackage ./apps/nix-packages/nix-packages.nix {};
    scratchpad = pkgs.callPackage ./apps/scratchpad/scratchpad.nix {};
    windows = pkgs.callPackage ./apps/windows/windows.nix {};

    md2html = pkgs.callPackage ./utils/md2html/md2html.nix {};
    raise-or-open-url = pkgs.callPackage ./utils/raise-or-open-url/raise-or-open-url.nix {};
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
    "process-manager"
    "raise-or-open-url"
    "nix-packages"
    "scratchpad"
    "windows"
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
