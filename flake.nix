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
      webkit-shell = pkgs.callPackage ./apps/webkit-shell/webkit-shell.nix {};
      windows = pkgs.callPackage ./apps/windows/windows.nix {};
      wireless-networks = pkgs.callPackage ./apps/wireless-networks/wireless-networks.nix {};
      nix-packages = pkgs.callPackage ./apps/nix-packages/nix-packages.nix {};
      scratchpad = pkgs.callPackage ./apps/scratchpad/scratchpad.nix {};
      file-picker = pkgs.callPackage ./apps/file-picker/file-picker.nix {};

      md2html = pkgs.callPackage ./utils/md2html/md2html.nix {};
    };
  in {
    packages = forAllSystems packageSet;

    homeManagerModules.default = import ./hm.nix;
  };
}
