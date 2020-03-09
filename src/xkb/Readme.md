# Generate X11 Keyboard Extensions (XKB) files

You can find [a good overview of how XKB works and is used on Linux][1]
in the Arch Linux wiki.

[1]: https://wiki.archlinux.org/index.php/X_keyboard_extension

## How to add new/update keyboard files

1. Install files system-wide by copying them into `/usr/share/X11/xkb/symbols`
   (rumor has it that it is also possible to install keyboards for the current user
   by copying them into `~/.xkb/symbols/` but we weren't able to make it work.)
2. If you are installing a new locale, it needs to be added to "rules set"
   which is what configuration tools use to pick up which locales are available.

   These files can be found in `/usr/share/X11/xkb/rules/`,
   but sadly, this is quite the exercise, as the files are supposed to be auto-generated.
   For testing purposes,
   editing the `layoutList` section of `evdev.xml` manually
   (by duplicating an existing section)
   should be fine.
   The `configItem/name` should be same as the file name,
   and `variantList` should have a `variant` where the `configItem/name`
   is the name of the `xkb_symbols` block.

   In case you want to know more about this process
   and all the details of this ecosystem,
   see [this post][evdev] by Daniel Jozsef.
3. Clear the xkb cache,
    either by running `sudo rm /var/lib/xkb/*.xkm`,
    or (on Debian systems) `sudo dpkg-reconfigure xkb-data`
4. Add the locale to your set of available ones
   using Gnome Settings or a similar tool.
   Use the "Show Keyboard Layout" button to preview the layout.
   You might need to log out and in again for the new settings to apply correctly.

[evdev]: https://medium.com/@daniel.jozsef/the-bazaar-with-landmines-or-how-to-extend-xkb-the-right-way-b82de59a1f9a

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
