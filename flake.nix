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
      bookmarks = pkgs.callPackage ./bookmarks/bookmarks.nix {};
      chat = pkgs.callPackage ./chat/chat.nix {};
      dataset-viewer = pkgs.callPackage ./dataset-viewer/dataset-viewer.nix {};
      launcher = pkgs.callPackage ./launcher/launcher.nix {};
      md2html = pkgs.callPackage ./md2html/md2html.nix {};
      mdx-editor = pkgs.callPackage ./mdx-editor/mdx-editor.nix {};
      music = pkgs.callPackage ./music/music.nix {};
      notes = pkgs.callPackage ./notes/notes.nix {};
      process-manager = pkgs.callPackage ./process-manager/process-manager.nix {};
      raise-or-open-url = pkgs.callPackage ./raise-or-open-url/raise-or-open-url.nix {};
      reminder = pkgs.callPackage ./reminder/reminder.nix {};
      webkit-shell = pkgs.callPackage ./webkit-shell/webkit-shell.nix {};
      nix-packages = pkgs.callPackage ./nix-packages/nix-packages.nix {};
      scratchpad = pkgs.callPackage ./scratchpad/scratchpad.nix {};
    };
  in {
    packages = forAllSystems packageSet;

    homeManagerModules.default = import ./hm.nix;
  };
}
