from setuptools import setup

setup(name='softkbdgen',
      version='0.1',
      description='Generate soft keyboards for mobile operating systems.',
      url='https://github.com/bbqsrc/softkbdgen',
      author='Brendan Molloy',
      author_email='brendan@bbqsrc.net',
      license='MIT',
      packages=['softkbdgen'],
      include_package_data=True,
      entry_points = {
          'console_scripts': ['softkbdgen=softkbdgen.__main__:main']
      })
