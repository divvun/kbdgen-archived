# Introduction

The `ios` target customises a fork of `tasty-imitation-keyboard` to add the necessary
localisation magic and integrate your chosen keyboard layouts.

# Prerequisites

You will need:

* Xcode
* MacPorts: https://guide.macports.org/chunked/installing.macports.html
* `tasty-imitation-keyboard` checked out somewhere (https://github.com/bbqsrc/tasty-imitation-keyboard)
* Imagemagick (for converting icons to their correct sizes)

# Running

Use the same command line options as you would for generating any other target, but use the `--repo` flag to supply the correct repository for generation.

Example: `kbdgen --repo local/path/to/tasty --target ios project.yaml`

The output will be found in the `build/ios/` directory. Open the `.xcodeproj` in Xcode to package the result.



