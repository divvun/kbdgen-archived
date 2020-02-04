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
