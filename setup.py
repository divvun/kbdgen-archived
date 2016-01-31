from setuptools import setup

with open('README.rst') as f:
    desc = f.read()

setup(name='kbdgen',
      version='0.2.0a1',
      description='Generate soft keyboards for mobile OSes and layouts for Windows, OS X and X11.',
      long_description=desc,
      url='https://github.com/bbqsrc/kbdgen',
      author='Brendan Molloy',
      author_email='brendan+pypi@bbqsrc.net',
      license='Apache-2.0',
      packages=['kbdgen'],
      keywords=['keyboard', 'generator', 'cldr'],
      include_package_data=True,
      install_requires=['PyYAML', 'pycountry'],
      classifiers=[
        "Development Status :: 4 - Beta",
        "License :: OSI Approved :: Apache Software License",
        "Programming Language :: Python :: 2",
        "Programming Language :: Python :: 2.6",
        "Programming Language :: Python :: 2.7",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.2",
        "Programming Language :: Python :: 3.3",
        "Programming Language :: Python :: 3.4",
        "Programming Language :: Python :: 3.5"
      ],
      entry_points = {
          'console_scripts': [
              'kbdgen=kbdgen.__main__:main',
              'cldr2kbdgen=kbdgen.cldr:cldr2kbdgen_main',
              'kbdgen2cldr=kbdgen.cldr:kbdgen2cldr_main'
          ]
      })
