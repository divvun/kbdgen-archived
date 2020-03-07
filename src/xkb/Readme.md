# Generate X11 Keyboard Extensions (XKB) files

You can find [a good overview of how XKB works and is used on Linux][1]
in the Arch Linux wiki.

[1]: https://wiki.archlinux.org/index.php/X_keyboard_extension

## How to add new/update keyboard files

1. Make sure the Gnome settings app (or a similar program) is not open
2. Install files
    - for the current user by copying them into `~/.xkb/symbols/`
    - or system-wide by copying them into `/usr/share/X11/xkb/symbols`
3. Clear the xkb cache,
    either by running `sudo rm /var/lib/xkb/*.xkm`,
    or (on Debian systems) `sudo dpkg-reconfigure xkb-data`

## Short description of xkb symbol files

It took me quite a while to find all this,
so here is a quick brain dump for other people looking at this code base,
(or Future Pascal).

The files of interest to us are the ones that contain `xkb_symbol` definitions.
Those are usually named just by their language code,
with no file extension.
You can find examples of such a files are
in the xkeyboard-config repository on freedesktop.org.
[The official one for Swedish keyboards][se]
or [the one for German keyboards][de]
make use of many of the available features
while also being easy to test.

[se]: https://gitlab.freedesktop.org/xkeyboard-config/xkeyboard-config/-/blob/835044ad75c5935958f93214b9e2d942afd07686/symbols/se
[de]: https://gitlab.freedesktop.org/xkeyboard-config/xkeyboard-config/-/blob/835044ad75c5935958f93214b9e2d942afd07686/symbols/de

The general structure of these files is as follows
(read `se` in as a placeholder for the filename):

- A `default [...] xkb_symbols` block is the block to include when referred to as `se`.
  This block is most often simply named `"basic"`.
- Other blocks are specializations.
  A block like `xkb_symbols "dvorak"` for example can be included like `se(dvorak)`.
  These blocks often start by including `se(basic)` and overwrite specific keys.
- Each block can contain several named groups, but this feature will not be used by us.
- The main thing in each block is the mapping of key codes to the symbols they should emit.
  Each mapping is from a key code to a list of symbols (one for each layer) for each group.
- You can check which key code is emitted by a key using the `xev` tool.
- The four default layers are `[base, shift, alt, alt+shift]`.
