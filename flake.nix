{
  inputs = {
    nixpkgs.url = "nixpkgs/nixpkgs-unstable";
  };

  outputs = {nixpkgs, ...}: let
    supportedSystems = ["x86_64-linux" "aarch64-linux" "x86_64-darwin" "aarch64-darwin"];

    forAllSystems = nixpkgs.lib.genAttrs supportedSystems;

    packageSet = system: let
      pkgs = nixpkgs.legacyPackages.${system};
    in {
      bookmarks = pkgs.callPackage ./apps/bookmarks/bookmarks.nix {};
      chat = pkgs.callPackage ./apps/chat/chat.nix {};
      dataset-viewer = pkgs.callPackage ./apps/dataset-viewer/dataset-viewer.nix {};
      launcher = pkgs.callPackage ./apps/launcher/launcher.nix {};
      music = pkgs.callPackage ./apps/music/music.nix {};
      notes = pkgs.callPackage ./apps/notes/notes.nix {};
      process-manager = pkgs.callPackage ./apps/process-manager/process-manager.nix {};
      reminder = pkgs.callPackage ./apps/reminder/reminder.nix {};
      webkit-shell = pkgs.callPackage ./apps/webkit-shell/webkit-shell.nix {};
      windows = pkgs.callPackage ./apps/windows/windows.nix {};
      nix-packages = pkgs.callPackage ./apps/nix-packages/nix-packages.nix {};
      scratchpad = pkgs.callPackage ./apps/scratchpad/scratchpad.nix {};

      md2html = pkgs.callPackage ./utils/md2html/md2html.nix {};
      raise-or-open-url = pkgs.callPackage ./utils/raise-or-open-url/raise-or-open-url.nix {};
    };
  in {
    packages = forAllSystems packageSet;

    homeManagerModules.default = import ./hm.nix;
  };
}
