## Introduction

There are several parts to a keyboard project. A project will have a project file, and one or more key board descriptors, both of which as YAML files. Depending on their purpose, the project may be configured to work with a specific target output, or several, depending on the developers requirements.

## Target

A target is the build output. Currently supported targets are:

* **android**: Android
* **ios**: iOS 8+
* **osx**: OS X
* **svg**: Scalable Vector Graphics output
* **win**: Windows 7+ (not mobile)
* **x11**: X11 format (**EXPERIMENTAL**)

## Project layout

In general, you will have a single **project** file `project.yaml` with several other **keyboard descriptors**:

    project.yaml
    sjd.yaml
    sme.yaml
    swe.yaml

### Project file

A project file describes content relevant to the entire project, such as which keyboard descriptors to include, binary signing information, the container name for some project builds, etc.

A very simple project file configured only for Android might look like this:

```yaml
internalName: keyboards

locales:
  en:
    name: My Keyboards
    description: A package of my keyboards!

author: Brendan Molloy
email: brendan@bbqsrc.net

layouts: [layout1, layout2]

version: "1.0"
build: "1"

targets:
  android:
    packageId: so.brendan.keyboards.sami
```

Each documentation target breaks down the relevant properties of the project files.

### Keyboard descriptor file

A keyboard descriptor describes each keyboard layout. It contains localisation, the key layouts themselves ("modes"), long press keys, dead keys, key combinations, etc.

A very simple keyboard file targetting Android might look like this:

```yaml
internalName: northern_sami

displayNames:
  se: Sámegiella
  en: Northern Sami
  nb: Nordsamisk

locale: se

modes:
  default: |
    á š e r t y u i o p ŋ
    a s d f g h j k l đ ŧ
    ž z č c v b n m w
  shift: |
    Á Š E R T Y U I O P Ŋ
    A S D F G H J K L Đ Ŧ
    Ž Z Č C V B N M W

targets:
  android:
    minimumSdk: 21

strings:
  space: gaske
  return: linnjámolsun
```

Each documentation target breaks down the relevant properties of the keyboard descriptor files.

