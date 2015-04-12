from setuptools import setup

setup(name='softkbdgen',
      version='0.2.0a1',
      description='Generate soft keyboards for mobile operating systems and keyboard layouts for Windows, OS X and Linux.',
      url='https://github.com/bbqsrc/softkbdgen',
      author='Brendan Molloy',
      author_email='brendan@bbqsrc.net',
      license='MIT',
      packages=['softkbdgen'],
      include_package_data=True,
      entry_points = {
          'console_scripts': [
              'softkbdgen=softkbdgen.__main__:main',
              'cldr-kbd2yaml=softkbdgen.cldr:kbd2yaml_main',
              'cldr-yaml2kbd=softkbdgen.cldr:yaml2kbd_main'
          ]
      })
