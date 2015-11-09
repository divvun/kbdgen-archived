# Introduction

The `osx` target generates a `.pkg` file, optionally codesigned, that installs a series of `.keylayout` files for each layout provided in the project.

# Dependencies

* This target can only be generated on an OS X system.
* lxml

# Target-specific configuration

## Project properties

The project properties are basically the same as `ios` except the icon is
an `icns` file.

```yaml
osx:
  codeSignId: "OS X Development"
  provisioningProfileId: Test
  packageId: so.brendan.keyboards.sami
  icon: an.icns
```

## Keyboard descriptor properties

The OS X target supports a few custom modes to facilitate the differences between OS X keyboards and others. Particularly, the `cmd` key is OS X specific.

Therefore, OS X specific modes are supported with the `osx-` prefix.

It is important to supply at least an `osx-cmd` mode otherwise the `cmd` key will have no function whatsoever.

If you wish to use your `iso-default` mode as the `osx-cmd` mode (which is the sanest default), you can use YAML referencing:

```yaml
iso-default: | &default
  my keyboard here
osx-cmd: *default
```

