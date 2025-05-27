{
  config,
  lib,
  pkgs,
  ...
}: let
  cfg = config.programs.vibeapps;

  # Get the vibeapps flake packages
  vibeappsFlake = builtins.getFlake (toString ./.);
  vibeappsPackages = vibeappsFlake.packages.${pkgs.system};

  # Define all available programs
  programNames = [
    "bookmarks"
    "chat"
    "dataset-viewer"
    "firefox-bookmarks"
    "launcher"
    "md2html"
    "mdx-editor"
    "music"
    "notes"
    "raise-or-open-url"
    "reminder"
    "webkit-shell"
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
    home.activation.killLauncher = lib.mkIf (cfg.enableAll || cfg.launcher.enable) (
      lib.hm.dag.entryAfter ["writeBoundary"] ''
        $DRY_RUN_CMD ${pkgs.procps}/bin/pkill -f launcher || true
      ''
    );
  };
}
