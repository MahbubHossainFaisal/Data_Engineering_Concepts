# setup.py

from setuptools import setup, find_packages

setup(
    name='python_package',
    version='0.1.0',
    packages=find_packages(),
    description='A simple example Python package',
    long_description=open('README.md').read(),
    long_description_content_type='text/markdown',
    url='https://github.com/mahbubhossainfaisal/Data_Engineering_Concepts/Software_Engineering_Principles/python_package',  # Update with your repository
    author='Mahbub Hossain Faisal',
    author_email='mahbubhossain249@gmail.com',
    license='MIT',  # Choose a license
    classifiers=[
        'Programming Language :: Python :: 3',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
    ],
    python_requires='>=3.6',
)
