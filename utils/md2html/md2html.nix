{
  pkgs,
  lib,
  ...
}:
pkgs.stdenvNoCC.mkDerivation {
  name = "md2html";
  outputHashAlgo = "sha256";
  outputHashMode = "recursive";
  outputHash = "sha256-Q02ANM9LZ6hIODq4/x4sAw4yQwOs5X1V3hFhnoilNEo=";
  src = ./.;

  buildPhase = ''
    mkdir -p $out/{bin,share/md2html}
    substituteInPlace md2html.js --replace-fail "@@CSS@@" "md2html.css"
    ${lib.getExe pkgs.bun} install
    ${lib.getExe pkgs.bun} build md2html.js --outdir $out/share/md2html --target node --sourcemap --minify
    chmod +x $out/share/md2html/md2html.js
    ln -s $out/share/md2html/md2html.js $out/bin/md2html
  '';
}
