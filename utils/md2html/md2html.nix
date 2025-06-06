{
  pkgs,
  lib,
  ...
}: let
  deps = pkgs.runCommand "md2html-deps" {
    nativeBuildInputs = [ pkgs.bun ];
  } ''
    mkdir -p $out
    cd $out
    ${lib.getExe pkgs.bun} add rehype-autolink-headings rehype-document rehype-format rehype-highlight rehype-raw rehype-slug rehype-stringify remark-definition-list remark-frontmatter remark-gfm remark-mdx remark-oembed remark-parse remark-rehype remark-wiki-link unified
  '';
in
  pkgs.stdenvNoCC.mkDerivation {
    name = "md2html";
    dontUnpack = true;
    src = ./.;
    buildPhase = ''
      mkdir -p $out/{bin,share/md2html}
      cp -r $src/* $out/share/md2html
      cp -r ${deps} $out/share/md2html/node_modules
      chmod +x $out/share/md2html/md2html.js
      ln -s $out/share/md2html/md2html.js $out/bin/md2html
      substituteInPlace $out/bin/md2html --replace-fail "@@CSS@@" "${./md2html.css}"
    '';
  }
