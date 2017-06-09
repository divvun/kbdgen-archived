# Introduction

The `ios` target customises a fork of `giellakbd-ios` to add the necessary
localisation magic and integrate your chosen keyboard layouts.

# Prerequisites

You will need:

* `giellakbd-ios` (https://github.com/divvun/giellakbd-ios)

# Running

Use the same command line options as you would for generating any other target, but use the `-r` flag to supply the correct repository for generation.

Example: `kbdgen -r local/path/to/giellakbd-ios -t ios project.yaml`

The output will be found in the `ios-build/` directory. Open the `.xcodeproj` in Xcode to package the result.

## Project properties

```yaml
targets:
  ios:
    bundleName: "Brendan's Keyboards"
    packageId: so.brendan.keyboards.sami
    codeSignId: "macOS Installer Certificate ID (find in your Keychain)"
    icon: any.png
    aboutDir: path/to/about/files # Should contain {locale}.txt files
```

The `aboutDir` directory should contain the text to be shown in the about screen of the hosting app.