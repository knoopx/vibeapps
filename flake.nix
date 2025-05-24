{
  inputs = {
    nixpkgs.url = "nixpkgs/nixpkgs-unstable";
  };

  outputs = {nixpkgs, ...}: let
    system = "x86_64-linux";
    pkgs = nixpkgs.legacyPackages.${system};
  in {
    packages.x86_64-linux = {
      chat = pkgs.callPackage ./chat/chat.nix {};
      dataset-viewer = pkgs.callPackage ./dataset-viewer/dataset-viewer.nix {};
      launcher = pkgs.callPackage ./launcher/launcher.nix {};
      md2html = pkgs.callPackage ./md2html/md2html.nix {};
      mdx-editor = pkgs.callPackage ./mdx-editor/mdx-editor.nix {};
      music = pkgs.callPackage ./music/music.nix {};
      notes = pkgs.callPackage ./notes/notes.nix {};
      raise-or-open-url = pkgs.callPackage ./raise-or-open-url/raise-or-open-url.nix {};
      reminder = pkgs.callPackage ./reminder/reminder.nix {};
      webkit-shell = pkgs.callPackage ./webkit-shell/webkit-shell.nix {};
      nix-packages = pkgs.callPackage ./nix-packages/nix-packages.nix {};
      scratchpad = pkgs.callPackage ./scratchpad/scratchpad.nix {};
    };
  };
}
