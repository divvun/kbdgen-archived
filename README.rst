kbdgen
======

.. image:: https://travis-ci.org/divvun/kbdgen.svg?branch=master
    :target: https://travis-ci.org/divvun/kbdgen

Generate keyboards and keyboard layouts for various operating systems.
Layout definitions for various languages can be found  `here <https://github.com/giellalt/>`__
(all repos starting with ``keyboard-``).

Requires Python 3.7 or higher.

* `Documentation <https://divvun.github.io/kbdgen/>`__

Installation
------------

From PyPI
~~~~~~~~~

::

    $ pip install kbdgen

From source
~~~~~~~~~~~

Assuming the current working directory is a checked out version of this
repo:

::

    $ poetry install

If you are on Linux, ensure you have the development package for Python 3 installed,
or you will receive build errors when you attempt to install.

You can also use the tools in development easily without installing:

::

    $ python -m kbdgen [...]

This will run the primary ``kbdgen`` tool. You may also access the CLDR
tooling my this method:

::

    $ python -m kbdgen.cldr {cldr2kbdgen,kbdgen2cldr} [...]

Targets
-------

The following targets are currently supported by ``kbdgen``:

-  Android (built on Linux or macOS)
-  iOS (built on macOS)
-  Windows 7 and later (source generated on any OS, built on Windows)
-  macOS (built on macOS)
-  X11 (built on any OS)
-  SVG (built on any OS)

The code is known to run well on macOS and Linux. Different generators
have different OS requirements as specified in their documentation.

Patches to extend support more broadly and add further targets are
highly welcomed!

Housekeeping
------------

To generate the documentation, run ``asciidoctor index.adoc`` in the ``docs`` directory.

License
-------

Apache 2 license. See LICENSE.

Thanks
------

Development of this project was sponsored by `UiT The Arctic University
of Norway <https://en.uit.no/>`__.
