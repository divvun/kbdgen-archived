## Required software

* Microsoft Keyboard Layout Creator
  * <http://www.microsoft.com/en-us/download/details.aspx?id=22339>

## Usage

Just run `softkbdgen` with `--target win` to generate the MS Keyboard Layout
Creator `.klc` files for your project.

The generated files will be found in `build/win/<internalName>/<layout>.klc`.

Simply load the generated files in MSKLC, and select
`Project > Build DDL and Setup Package` to generate an installer for 32-bit
and 64-bit versions of Windows. Compatibility can only be guaranteed for
Windows 7 and later.

## Mappings between modes in descriptor files and Windows keyboards

- **iso-default**: Base keyboard
- **iso-shift**: Shift pressed
- **iso-caps**: Caps lock enabled
- **iso-alt**: AltGr (or Ctrl+Alt if keyboard missing AltGr) pressed
- **iso-alt+caps**: AltGr plus caps lock
- **iso-alt+shift**: AltGr plus shift
- **iso-ctrl**: Ctrl pressed (mostly will not work due to OS-level key combinations overriding this layer)

Any other modes are ignored by this target.

## Other useful information

* Windows keyboard identifiers must be unique, are 8 characters long and
  begin with `kbd`. The next 5 characters are generated from the next 5
  alphanumeric characters of the keyboard's `internalName`. For example, if
  the `internalName` of a keyboard is `se-1-foo`, the internal keyboard name
  for Windows will be `kbdse1fo`.
* Windows does not support Unicode ligatures in deadkeys, but does support
  them as ordinary keys.
* Most warnings shown by the verifier in MSKLC do not affect the utility of
  the keyboard and are sometimes false positives. For example, MSKLC fails to
  recognise that a key missing on some keyboards can be generated using a
  deadkey combination.
