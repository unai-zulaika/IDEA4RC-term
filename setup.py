from setuptools import setup, find_packages

setup(
    name='term_matcher',  # Name of your package
    version='0.21',        # Initial version
    # Short description
    description='A library for fuzzy matching terms in text with corresponding codes.',
    # Long description from README.md
    long_description=open('README.md').read(),
    # Specifies the format of long description
    long_description_content_type='text/markdown',
    author='Unai Zulaika',  # Author's name
    author_email='unai.zulaika@deusto.es',  # Author's email
    url='https://github.com/unai-zulaika/term_matcher',  # URL to the repository
    packages=find_packages(),  # Automatically find packages in the project
    install_requires=[  # List of dependencies
        'rapidfuzz',
        'tqdm'
    ],
    classifiers=[  # Classifiers help users find your project
        'Programming Language :: Python :: 3',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Intended Audience :: Developers',
        'Topic :: Software Development :: Libraries',
    ],
    python_requires='>=3.6',  # Specify minimum Python version
    keywords='fuzzy matching terms codes',  # Keywords for package search
)
