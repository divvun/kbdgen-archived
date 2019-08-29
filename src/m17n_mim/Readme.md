# Notes on IBus and M17N

## How to add new M17n languages on Ubuntu 18.04

1. Make sure Gnome settings app is not open
2. Copy the new `.mim` file(s) to either `~/.m17n.d/` (user local) or `/usr/share/m17n/` (global)
3. Make sure they have the correct permissions set,
    i.e. `644` like the other files
4. restart all IBus daemons (According to [the Internet](https://askubuntu.com/a/656243)),
    e.g. using `pgrep ibus | xargs kill`
5. Open Gnome settings
    1. Go to "Region & Language"
    2. Under "Input Sources", press the "+" button
    3. In the modal window, select your newly added language variant.
        Note that it might be grouped by the main language,
        e.g., you might need to click on "Swedish (Sweden)" first,
        and then select the specific variant like "Swedish (test (m17n))".
    4. Confirm with "Add"
    5. You can test the keyboard layout by clicking on the "eye" icon
        next to the language in the list
6. The language should show up global menu bar's language selection.
7. Enjoy your life.

## Definitions

IME: Input method engine

IBus:
- "Intelligent Input Bus"
- Linux-based IME for non-Latin characters.
- Think typing chinese characters using a US keyboard: You type the phonetic spelling and get suggestions for characters on the screen to choose from.
- cf. [Wikipedia](https://en.wikipedia.org/wiki/Intelligent_Input_Bus), [ArchWiki](https://wiki.archlinux.org/index.php/IBus)
- [source](https://github.com/ibus/ibus)

M17n:
- abbr. of "multilingualization"
- implementation and database of locales and input methods
- [ibus-m17n](https://github.com/ibus/ibus-m17n) uses this as a source for IBus
- cf. [nongnu.org/m17n](https://www.nongnu.org/m17n/)
- library represents multilingual text as an object named M-text and has functions to deal with them

M-Text:
- "M-text is a string with attributes called text properties, and designed to substitute for string in C" ([nongnu.org/m17n](https://www.nongnu.org/m17n/))

## Interesting findings

### What language codes in `mim` files are used

It appears that they follow [ISO 639][iso639],
in an interesting way:

- For many languages, the two letter codes from ISO 639-1 are used
- For languages that are not in 639-1, they "fall back" to the newer version, ISO 639-2.

[iso639]: https://www.loc.gov/standards/iso639-2/php/code_list.php
