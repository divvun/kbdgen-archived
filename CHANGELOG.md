# Version 0.2

## Features

* Add X11, Windows, OS X, SVG target support
* Add CLDR convertor (both directions)

## Changes

* Android env var becomes `ANDROID_HOME`
* Keyboard layout mode format is no longer a list.

This:

> default: [
>   A B C,
>   D E F
> ]

Becomes:

> default: |
>   A B C
>   D E F

# Version 0.1

* Initial release, supporting iOS and Android.
