import sys, os
from setuptools import setup, find_packages

# Import the file that contains the version number.
src_dir = os.path.join(os.path.dirname(__file__), 'src', 'pyexist')
sys.path.insert(0, src_dir)
from version import __version__

# Import the project description from the README.
readme = open('README').read()
start  = readme.index('\n\n')
end    = readme.index('\n\n=')
descr  = readme[start:end].strip()

# Run the setup.
setup(name             = 'pyexist',
      version          = __version__,
      description      = 'A simple wrapper around eXist-db',
      long_description = descr,
      author           = 'Samuel Abels',
      author_email     = 'knipknap@gmail.com',
      license          = 'GPLv2',
      package_dir      = {'': 'src'},
      packages         = [p for p in find_packages('src')],
      scripts          = ['pyexist'],
      install_requires = ['lxml'],
      keywords         = ' '.join(['pyexist',
                                   'database',
                                   'xml',
                                   'wrapper',
                                   'exist-db',
                                   'exist']),
      url              = 'http://github.com/knipknap/pyexist',
      classifiers      = [
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: GNU General Public License (GPL)',
        'Programming Language :: Python',
        'Topic :: Software Development :: Libraries',
        'Topic :: Software Development :: Libraries :: Python Modules',
        'Topic :: Text Processing :: Markup :: XML'
      ])
