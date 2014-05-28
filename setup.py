from distutils2.core import setup

setup(
  name='hypertex',
  version='0',
  description="HyperTeX",
  url='http://github.com/adeel/hypertex',
  author='Adeel Khan',
  author_email='kadeel@gmail.com',
  packages=['hypertex', 'hypertex.render'],
  scripts=['bin/hypertex'],
  package_data={
    'hypertex.render': ['html/*.html', 'tex/*.tex']
  },
  install_requires=['Jinja2', 'lxml', ],
  license='MIT',
  classifiers=[
    'Development Status :: 4 - Beta',
    'Environment :: Console',
    'Operating System :: POSIX',
    # 'Topic :: Utilities',
  ]
)