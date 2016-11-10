## Unicode escaping

Sometimes you want to use a key that either can't be seen in a text editor, or
will mangle your text editor (like zero width spacing).

Escaping is quite simple. Use `\u{}` notation for `U+xxxx` codepoints. For example, non-breaking space `0x00A0` can be represented as `\u{0a}`.

## Required keys

* **internalName**: internal name for the keyboard.
* **displayNames**: a map of locales and the name for the keyboard in that locale. Recommended to have the display name for at least `en` and the locale of the keyboard itself.
* **locale**: the preferred locale for the keyboard. If possible, use the two-character ISO code, as the three-character codes are not universally supported.
* **modes**: a map of keyboard layouts. See section below to see which keys are supported.

### Modes

### Valid keys

For touch keyboards, there are two modes:

* **default**: default keyboard layout
* **shift**: shifted keyboard layout

The format is unrestricted, but nominally, unless you have a good reason to do so, you should not have more than 3 rows, and no more than 12 keys on the top two rows, and 10 on the bottom row.

For physical keyboards, things are more complex:

* **iso-default**: default
* **iso-shift**: shift pressed
* **iso-caps**: caps lock enabled
* **iso-alt**: AltGr (or option) key pressed
* **iso-caps+alt**: caps lock enabled + AltGr/Opt
* **iso-caps+shift**: caps lock enabled + shift
* **iso-alt+shift**: AltGr/Opt + shift
* **iso-caps+alt+shift**: caps lock enabled + AltGr/Opt + Shift

There are further platform-specific keys in some cases, and they are defined in the relevant target documentation.

### Mode formats

There are two ways to define a keyboard mode: as a string or as a map.

As a string is the easiest way to visually see what is going on:

```yaml
  default: |
    q w e r t z u i o p ú
    a s d f g h j k l ů
    y x c v b n m

  iso-default: |
    < + ě š č ř ž ý á í é = '
    q w e r t z u i o p ú )
    a s d f g h j k l ů § ¨
    \ y x c v b n m , . -
```

Note the pipe symbol (`|`) at the end of the key. Without it, the new lines are stripped.

If you are creating a layout that doesn't need more than a few keys defined, it may be more appropriate to use the map mode, which uses the ISO key numbering for handling placement.

```yaml
  iso-alt:
    E01: "`"
    E02: "@"
    E03: "#"
    E04: $
    E05: "~"
```

A handy reference keyboard image with the ISO keys listed can be found below.

<!-- TODO: IMAGE GOES HERE -->


## Conditional keys

### Touch layouts

* **longPress**: a map of keys and a space-separated list of characters to appear in the long press popout.

```yaml
longPress:
  a: å à ä
  o: ø ö
```

### Physical layouts

* **deadKeys**: a map of lists of keys from a mode where the key should behave as a deadkey.

Example:

```yaml
deadKeys:
  iso-default: ['`']
```

* **transforms**: a cascading map of transforms, (usually) starting with a deadkey. Use a `' '` to denote the fallback when the next key pressed is not a transform state (or is space).

For example, a transform for pressing `a`, `b` and then `c` and outputting `OUTPUT` would look like below.

```yaml
transforms:
  a:
    ' ': a
    b:
      ' ': b
      c: OUTPUT
```

* **decimal**: specify the decimal point value (basically just for numpads on Windows). Usually a `.` or `,`.
* **special**: a map of special cases for various keys. Supported keys are:
  * **space**: some layouts require changing the spacebar key to output differently. Example:

```yaml
special:
  space:
    iso-alt: \u{A0}
    iso-caps+alt: \u{A0}
    iso-alt+shift: \u{A0}
```

That example changes the spacebar in the given modes to output a non-breaking space.
