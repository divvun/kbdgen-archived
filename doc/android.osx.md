# Prerequisites

You will need:

* This codebase somewhere on your hard drive.
* Xcode (at least the command line tools)
* MacPorts: https://guide.macports.org/chunked/installing.macports.html
* JDK 7: http://www.oracle.com/technetwork/java/javase/downloads/jdk7-downloads-1880260.html
* Android SDK (click "VIEW ALL DOWNLOADS AND SIZES" and choose from "SDK Tools Only"): https://developer.android.com/sdk/index.html?hl=i
* GiellaIME checked out somewhere (https://github.com/bbqsrc/giella-ime)

# Installation

1. Install MacPorts.
2. Install JDK 7.
3. Unzip the Android SDK somewhere. I will assume you unzipped it to `~/sdks`
4. As root: `port install apache-ant python3.4 py34-pip`
5. As root: `pip3.4 install pycountry lxml PyYAML`
6. Run: `export ANDROID_SDK="~/sdks/android-sdk-macosx"`, replacing the string with where you put the directory.
7. Run: `$ANDROID_SDK/tools/android update sdk -u -t "tools,platform-tools,build-tools-19.1.0,extra-android-support,android-19"`. Say yes to all the EULAs.
8. Done!

# Running

1. Run `export ANDROID_SDK="~/sdks/android-sdk-macosx"`, replacing the string with where you put the directory.
2. In the `softkbdgen` directory, run `python3.4 softkbdgen.py --help` to see the help text.

An example: `python3.4 softkbdgen.py --repo local/path/to/giella-ime --target android project.yaml`

You can also substitute a local path to a git repo to the remote path and the
application will automatically check it out for you.

# Testing on a device

1. Plug your Android device in.
2. Run `ANDROID_SDK/platform-tools/adb install -r <path to apk>`

If it spits errors, uninstall the package off your device first.

## Build files

Files will be placed in the `build/` directory. In debug mode, a file by the
name of `<project internalName>-debug.apk` will appear, while in release mode
(when provided with `-R` flag), `<project internalName>-release.apk` will
appear.

The release APK can be used to be uploaded to the Play Store.

# Examples

See the `sme.yaml` and `sjd.yaml` files for examples of keyboard layouts.

See the `project.yaml` file for an example of project files.

# Syntax

## Projects

Your project files must have at least the following properties: `author`,
`email`, `locales`, `layouts`, and in most cases, `targets`.


`author` and `email` are pretty straight forward:

```yaml
author: Your name
email: Your email
```

`locales` are also quite straight forward. You provide a map of locales to a
`name` and `description` property in the language being localised to.

```yaml
locales:
  en:
    name: The package name in English.
    description: A description of the package in English.
  nb:
    name: Any other language you want, using its ISO 639-1 format.
    description: Other locales are not supported for localisation on Android. :(
```

`layouts` refers to the keyboard layout descriptors you wish to include in
this package.

```yaml
layouts: [smj, sjd]
```

`targets` defines target-specific configuration.

The Android-specific configuration keys are:

* *packageId (required)*: the reverse-domain notation ID for the package

If you are planning to generate an APK for release, [it must be signed](http://developer.android.com/tools/publishing/app-signing.html).

If you wish to sign your packages, you need to provide the following:

* *keyStore*: the absolute path to your keystore (see section "Generating keystores")
* *keyAlias*: the alias for the key in the keystore (as above)

```yaml
targets:
  android:
    packageId: com.example.amazing.keyboards
    keyStore: /absolute/path/to/my/keystore
    keyAlias: alias_specified_during_generation
```

## Keyboards

Your keyboard layout descriptor has the following required properties:
`internalName`, `displayNames`, `locale`, and `modes`. Optionally, you may
also include `longpress` and `styles`.

`internalName` is required for file naming and other internal identification
purposes. Please use lower case ASCII characters and underscores eg
`some_name` to avoid any issues during compilation.

```yaml
internalName: my_keyboard
```

`displayNames` is a map of localised display names for your keyboard. These
locales may be ISO 639-3 if you so desire, although for maximum
compatibility, use 639-1 where possible.

```yaml
displayNames:
  en: Kildin Sami
  nb: kildinsamisk
```

`modes` is a map of the several modes available, with layouts provided.
Currently supported modes are `default` and `shift`. `default` is required.

```yaml
modes:
  default: [
    á š e r t y u i o p ŋ,
    a s d f g h j k l đ ŧ,
    ž z č c v b n m w
  ]
  shift: [
    Á Š E R T Y U I O P Ŋ,
    A S D F G H J K L Đ Ŧ,
    Ž Z Č C V B N M W
  ]
```

`longpress` allows one to determine which keys appear in the long press menu,
per key.

```yaml
longpress:
  Á: Q
  A: Æ Ä Å
  Č: X
  O: Ø Ö
  á: q
  a: æ ä å
  č: x
  o: ø ö
```

`styles` is a map that allows you to more closely fine tune the appearance
of the keyboard.

At the moment, it only controls action keys, such as the return key or shift
buttons, with the `action` property. This property supports the properties
`tablet` and `phone`, with each of those supporting `backspace`, `enter`
and `shift`.

Those three action key properties take a list of values: row, side, width.
The width parameter supports the keyword `fill` which fills remaining
space, or a percentage.

```yaml
styles:
  tablet:
    actions:
      backspace: [1, right, fill]
      enter: [2, right, fill]
      shift: [3, both, fill]
  phone:
    actions:
      shift: [3, left, fill]
      backspace: [3, right, fill]
```

# Generating keystores

Make sure you've read the
["Signing Your Applications"](http://developer.android.com/tools/publishing/app-signing.html)
page from the Android Developers website.

It is recommended that you use 4096-bit keys, and name the keystore and
alias your key with the internal name of your project.

For example, if my project name was "sami_keyboard", adn I wanted the key to
last for 10000 days, I would run the following command:

`keytool -genkey -v -keystore sami_keyboard.keystore -alias sami_keyboard -keyalg RSA -keysize 4096 -validity 10000`

*Make sure you keep your key safe! Don't publish it to git or svn.*

The warning straight from the Android website says:

> Warning: Keep your keystore and private key in a safe and secure place,
> and ensure that you have secure backups of them. If you publish an app to
> Google Play and then lose the key with which you signed your app, you will
> not be able to publish any updates to your app, since you must always sign
> all versions of your app with the same key.
