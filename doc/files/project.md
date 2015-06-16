## Required keys

* *internal_name*: [A-Za-z0-9\_] only. Used in various places internally and for file names in some targets.
* *locales*: at least the `en` locale must be defined. It is a map of `name` and `description`, eg:

```yaml
locales:
  en:
    name: My Keyboards
    description: A package of my keyboards!
```

* *author*: a string of author(s).
* *email*: a string of email(s).
* *layouts*: a list of keyboard descriptors to use. If there is one file, and it is `foo.yaml`, then you would write `[foo]`.
* *version*: a string, preferably in semantic versioning (X.Y.Z) format.
* *build*: a stringified integer that should be incremented for every release, as some targets will break (eg iOS, Android) when upgrading if you do not do this.

## Conditional keys

* *targets*: a map of target-specific configuration options. These are documented in each target's documentation if necessary.
