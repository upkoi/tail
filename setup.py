from setuptools import setup
from setuptools import find_packages

setup(name='TAIL',
      version='1.0.5',
      description='Tampa AI League',
      long_description='The Tampa AI League official examples & qualification tool',
      author='Rob Venables',
      author_email='rob@upkoi.com',
      url='https://github.com/upkoi/tail',
      license='MIT',
      install_requires=['skypond>=0.2.0',
                        'numpy>=1.9.1',
                        'docker>=3.7.2',
                        'gym>=0.12.1',
                        'tqdm',
                        'ethereum',
                        'profanity',
                        'sparklines'],
      classifiers=[
          'Development Status :: 3 - Alpha',
          'Intended Audience :: Developers',
          'Intended Audience :: Education',
          'Intended Audience :: Science/Research',
          'License :: OSI Approved :: MIT License',
          'Programming Language :: Python :: 3',
          'Programming Language :: Python :: 3.6',
      ],
      packages=find_packages())
