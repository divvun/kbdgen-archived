## Required software

* Microsoft Keyboard Layout Creator
  * <http://www.microsoft.com/en-us/download/details.aspx?id=22339>

## Usage

Just run `kbdgen` with `--target win` to generate the MS Keyboard Layout
Creator `.klc` files for your project.

The generated files will be found in `build/win/<internalName>/<layout>.klc`.

Simply load the generated files in MSKLC, and select
`Project > Build DDL and Setup Package` to generate an installer for 32-bit
and 64-bit versions of Windows. Compatibility can only be guaranteed for
Windows 7 and later.

## Mappings between modes in descriptor files and Windows keyboards

- **iso-default**: Base keyboard
- **iso-shift**: Shift pressed
- **iso-alt**: AltGr (or Ctrl+Alt if keyboard missing AltGr) pressed
- **iso-alt+shift**: AltGr plus shift
- **iso-caps+alt**: AltGr plus caps lock
- **iso-ctrl**: Ctrl pressed (mostly will not work due to OS-level key combinations overriding this layer)

Two special cases with limitations listed below:

- **iso-caps**: Caps lock enabled
- **iso-caps+shift**: Caps lock and shift pressed

If both of the above modes are found, some limitations will apply as described
in the section below.

Any other modes are ignored by this target.

## Testing

You can test the keyboard in MSKLC under `Project > Test Keyboard Layout...`.
A text field appears with the currently open keyboard layout enabled.

To test it in the OS itself, just build the keyboard as described, and run
the installer. You must uninstall the keyboard before you can install it
again.

## Limitations

* Windows does not support Unicode ligatures in deadkeys, but does support
  them as ordinary keys.
* Using `iso-caps` and `iso-caps+shift` with Windows is limited to single
  codepoints, as the ligature limitation also applies here.
* Windows keyboard identifiers must be unique, are 8 characters long and
  begin with `kbd`. The next 5 characters are generated from the next 5
  alphanumeric characters of the keyboard's `internalName`. For example, if
  the `internalName` of a keyboard is `se-1-foo`, the internal keyboard name
  for Windows will be `kbdse1fo`.
* If a keyboard is generated with erroneous data, MSKLC does not provide any
  useful error information and merely complains that there was an error and
  the file cannot be opened. Please report these files as bugs on GitHub for
  investigation.

## Other useful information

* The keyboard visual layout can be changed under `View > Options` between
  three different keyboard variants. The typical ISO keyboard layout is the
  second option.
* Most warnings shown by the verifier in MSKLC do not affect the utility of
  the keyboard and are sometimes false positives. For example, MSKLC fails to
  recognise that a key missing on some keyboards can be generated using a
  deadkey combination.
* Some warnings can be disabled in `View > Options`. It is recommended to
  disable `Include Validation Warnings Related to Codepages` as the warnings
  are almost completely useless in the Unicode era.
