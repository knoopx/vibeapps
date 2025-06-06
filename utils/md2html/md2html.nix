{
  pkgs,
  lib,
  ...
}: let
  # Create a package.json and package-lock.json approach
  packageJson = pkgs.writeText "package.json" (builtins.toJSON {
    name = "md2html-deps";
    version = "1.0.0";
    dependencies = {
      "rehype-autolink-headings" = "^7.1.0";
      "rehype-document" = "^6.0.1";
      "rehype-format" = "^5.0.0";
      "rehype-highlight" = "^7.0.0";
      "rehype-raw" = "^7.0.0";
      "rehype-slug" = "^6.0.0";
      "rehype-stringify" = "^10.0.0";
      "remark-definition-list" = "^2.0.0";
      "remark-frontmatter" = "^5.0.0";
      "remark-gfm" = "^4.0.0";
      "remark-mdx" = "^3.0.1";
      "remark-oembed" = "^1.2.2";
      "remark-parse" = "^11.0.0";
      "remark-rehype" = "^11.1.0";
      "remark-wiki-link" = "^1.0.5";
      "unified" = "^11.0.4";
    };
  });

  # Most practical automatic solution: Use dream2nix or similar
  # For now, let's use a simple approach that uses bun and caches properly
  deps = pkgs.runCommand "md2html-deps" {
    nativeBuildInputs = [ pkgs.bun ];

    # Create a deterministic environment
    preferLocalBuild = true;
    allowSubstitutes = false;
  } ''
    mkdir -p $out
    cd $out

    # Copy package.json
    cp ${packageJson} package.json

    # Install dependencies using bun (which is faster and more reliable)
    export BUN_INSTALL_CACHE_DIR=$TMPDIR/bun-cache
    bun install --production --frozen-lockfile=false

    # Remove unnecessary files to make the output smaller
    find node_modules -name "*.md" -delete
    find node_modules -name "*.txt" -delete
    find node_modules -name "test" -type d -exec rm -rf {} + 2>/dev/null || true
    find node_modules -name "tests" -type d -exec rm -rf {} + 2>/dev/null || true
    find node_modules -name "*.test.js" -delete
    find node_modules -name "*.spec.js" -delete
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
