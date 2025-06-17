{
  pkgs,
  lib,
  ...
}: let
  src = pkgs.stdenvNoCC.mkDerivation {
    name = "md2html";
    outputHashAlgo = "sha256";
    outputHashMode = "recursive";
    outputHash = "sha256-cuh1MWEEZ4/rS6T/G9qxe3Nr7WTuH3wXwY6uFTZH1B4=";
    src = ./.;

    buildPhase = ''
      ${lib.getExe pkgs.bun} install
      ${lib.getExe pkgs.bun} build md2html.js --outdir $out --target node --sourcemap --minify
    '';
  };
in
  pkgs.stdenvNoCC.mkDerivation {
    name = "md2html";
    src = src;

    buildPhase = ''
      mkdir -p $out/{bin,share/md2html}
      cp ${./md2html.css} $out/share/md2html/md2html.css
      substituteInPlace md2html.js --replace-fail "@@CSS@@" "$out/share/md2html/md2html.css"
      cp md2html.js $out/share/md2html/md2html.js
      chmod +x $out/share/md2html/md2html.js
      ln -s $out/share/md2html/md2html.js $out/bin/md2html
    '';
  }
