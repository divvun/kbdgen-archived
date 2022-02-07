let
  moz_overlay = import (builtins.fetchTarball https://github.com/mozilla/nixpkgs-mozilla/archive/master.tar.gz);
  pkgs = import <nixpkgs> { overlays = [ moz_overlay ]; };
  rust = pkgs.latest.rustChannels.stable.rust.override { extensions = [ "clippy-preview" "rustfmt-preview" ]; };
in
  with pkgs;

mkShell {
  buildInputs = with pkgs; [
    rust
  ];
}
