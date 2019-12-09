import setuptools


def get_version():
    version = {}
    with open('tap_wonolo/version.py') as fp:
        exec(fp.read(), version)
    return version['__version__']


with open('README.md', 'r') as f:
    readme = f.read()


setuptools.setup(
    name='tap_wonolo',
    author='David Wallace',
    author_email='david.wallace@goodeggs.com',
    version=get_version(),
    url='https://github.com/goodeggs/tap-wonolo',
    description='Singer.io tap for extracting data from Wonolo REST API',
    long_description=readme,
    long_description_content_type='text/markdown',
    classifiers=[
        'License :: OSI Approved :: GNU General Public License v3 (GPLv3)',
        'Natural Language :: English',
        'Topic :: Software Development',
        'Intended Audience :: Developers',
        'Operating System :: OS Independent',
        'Development Status :: 5 - Production/Stable',
        'Programming Language :: Python :: 3 :: Only',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8'
    ],
    keywords="singer tap python wonolo",
    license='GPLv3',
    packages=setuptools.find_packages(exclude=['tests']),
    package_data={
        'tap_wonolo': ['schemas/*.json']
    },
    install_requires=[
        'requests>=2.22.0',
        'attrs>=19.3.0',
        'singer-python==5.8.1',
        'backoff==1.8.0',
        'rollbar>=0.14.7'
    ],
    python_requires='>=3.6',
    entry_points={
        'console_scripts': ['tap-wonolo = tap_wonolo:main']
    }
)
