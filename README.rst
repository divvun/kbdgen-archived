kbdgen
======

Generate keyboards and keyboard layouts for various operating systems.

Requires Python 3.

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

    $ pip install -r requirements.txt
    $ pip install .

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

-  Android (built on Linux or OS X)
-  iOS (built on OS X)
-  Windows 7 and later (source generated on any OS, built on Windows)
-  OS X (built on OS X)
-  X11 (built on any OS)
-  SVG (built on any OS)

The code is known to run well on OS X and Linux. Different generators
have different OS requirements as specified in their documentation.

Patches to extend support more broadly and add further targets are
highly welcomed!

Documentation
-------------

All documentation can be found in the ``docs`` directory. Once it's good
enough, it'll be published somewhere nice for easy access.

License
-------

Apache 2 license. See LICENSE.

Thanks
------

Development of this project was sponsored by `UiT The Arctic University
of Norway <https://en.uit.no/>`__.
