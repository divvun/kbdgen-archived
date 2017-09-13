# Introduction

The `android` target customises a fork of the Google Android LatinIME to add the necessary
localisation magic and integrate your chosen keyboard layouts.

# Prerequisites

You will need:

* [JDK 8](http://www.oracle.com/technetwork/java/javase/downloads/jdk8-downloads-2133151.html)
* [Android SDK CLI Tools](https://developer.android.com/studio/index.html#command-tools)

# Installation

**Warning:** you will need about 2.6GB of free space to install the Android SDK dependencies.

1. Create a directory to host your Android SDK.
2. Export `ANDROID_HOME` to point to this directory.
3. Unzip the Android SDK CLI tools into `$ANDROID_HOME` (so you have `$ANDROID_HOME/tools`).
4. Run `yes | $ANDROID_HOME/tools/bin/sdkmanager --licenses` to accept the licenses.
5. Run `$ANDROID_HOME/tools/bin/sdkmanager tools "build-tools;25.0.3" "extras;android;m2repository" ndk-bundle "platforms;android-25"` to install the required dependencies. This may take a long time, and will not show any progress of any kind.

You should save the `ANDROID_HOME` export into your `.profile` so the variable is set when your shell loads.

# Generating the keyboard APK

Run `kbdgen -t android -r path/to/giella-ime project.yaml`.

You can also substitute a local path to a git repo to the remote path and the
application will automatically check it out for you.

# Testing on a device

1. Plug your Android device in.
2. Run `$ANDROID_HOME/platform-tools/adb install -r <path to apk>`

If it spits errors, uninstall the package off your device first.

## Build files

Files will be placed in the directory specified by the `-o` flag or the current 
working directory. In debug mode, a file by the name of `<project internalName>-<version>_debug.apk` will appear, while in release mode (when provided with `-R` flag), `<project internalName>-<version>_release.apk` will
appear.

In order for the release build to be generated, signing keys must be provided (described in the configuration section below). The release APK can then be uploaded to the Play Store if desired.

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
* *icon (recommended)*: path to the icon file to be converted into the various
sizes required by Android

If you are planning to generate an APK for release, [it must be signed](http://developer.android.com/tools/publishing/app-signing.html).

If you wish to sign your packages, you need to provide the following:

* *keyStore*: the absolute or relative path to your keystore (see section "Generating keystores")
* *keyAlias*: the alias for the key in the keystore (as above)

```yaml
targets:
  android:
    packageId: com.example.amazing.keyboards
    icon: icon.png
    keyStore: path/to/my/keystore
    keyAlias: alias_specified_during_generation
```

## Keyboards

Your keyboard layout descriptor has the following required properties:
`internalName`, `displayNames`, `locale`, and `modes`. Optionally, you may
also include `longpress` and `styles`.

`internalName` is required for file naming and other internal identification
purposes. Please use lower case ASCII characters and underscores eg
`some_name` to avoid any issues during compilation.

It is considered best practice to keep the internal name short and relevant,
such as using the locale name only, and extending it for variants.

For example, several keyboards relating to `sme` might be named:

```yaml
internalName: sme
internalName: sme-no
internalName: sme-sv
internalName: sme-extended
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
  default: |
    á š e r t y u i o p ŋ
    a s d f g h j k l đ ŧ
    ž z č c v b n m w
  shift: |
    Á Š E R T Y U I O P Ŋ
    A S D F G H J K L Đ Ŧ
    Ž Z Č C V B N M W
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

### Target-specific configuration

Under the `targets.android` tree, the following properties are supported:

- `minimumSdk`: the API level that is the minimum supported for a keyboard. Useful for limiting access to a keyboard where it is known several glyphs are missing on older devices. [Click here for Android documentation on API versions compared to OS version](https://source.android.com/source/build-numbers.html).
- `showNumberHints`: defines where or not the number hints are shown on the top row of keys. When set to `false`, no number hints will be shown and any long press keys defined will be shown in their place. Defaults to `true`.

Note: the lowest API supported by this keyboard is API 16, but it *may* work
on older variants.

# Generating keystores

Make sure you've read the
["Signing Your Applications"](http://developer.android.com/tools/publishing/app-signing.html)
page from the Android Developers website.

It is recommended that you use 4096-bit keys, and name the keystore and
alias your key with the internal name of your project.

**Use ASCII characters only for your password if you value your sanity.**

For example, if my project name was "sami_keyboard", and I wanted the key to
last for 10000 days, I would run the following command:

`keytool -genkey -v -keystore sami_keyboard.keystore -alias sami_keyboard -keyalg RSA -keysize 4096 -validity 10000`

**Make sure you keep your key safe! Don't publish it to git or svn.**

The warning straight from the Android website says:

> Warning: Keep your keystore and private key in a safe and secure place,
> and ensure that you have secure backups of them. If you publish an app to
> Google Play and then lose the key with which you signed your app, you will
> not be able to publish any updates to your app, since you must always sign
> all versions of your app with the same key.
