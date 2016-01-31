from setuptools import setup

setup(name='kbdgen',
      version='0.2.0a1',
      description='Generate soft keyboards for mobile operating systems and keyboard layouts for Windows, OS X and Linux.',
      url='https://github.com/bbqsrc/kbdgen',
      author='Brendan Molloy',
      author_email='brendan@bbqsrc.net',
      license='MIT',
      packages=['kbdgen'],
      include_package_data=True,
      install_requires=['pyyaml', 'tornado', 'pycountry'],
      entry_points = {
          'console_scripts': [
              'kbdgen=kbdgen.__main__:main',
              'cldr2kbdgen=kbdgen.cldr:cldr2kbdgen_main',
              'kbdgen2cldr=kbdgen.cldr:kbdgen2cldr_main'
          ]
      })
