# Notes on IBus and M17N

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
