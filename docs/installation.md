# Installation

## macOS

You will need:

* This codebase somewhere on your hard drive.
* Xcode (at least the command line tools)
* [MacPorts](https://www.macports.org) or [Homebrew](http://brew.sh/)

### With MacPorts

```
port install python3.6 py36-pip imagemagick
pip3.5 install kbdgen
```

### With Homebrew

```
brew install python3 imagemagick
pip3 install kbdgen
```

### From source

If installing from source, change the `pip` line to:

```
pip3.6 install -r requirements.txt
pip3.6 install .
```

