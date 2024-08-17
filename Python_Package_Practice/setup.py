from setuptools import setup, find_packages

setup(
    name='data_toolkit',
    version='0.1.0',
    author='Mahbub Hossain Faisal',
    author_email='mahbbubhossain249@gmail.com',
    description='A toolkit for data loading, validation, transformation, and visualization',
    long_description=open('README.md').read(),
    long_description_content_type='text/markdown',
    url='https://github.com/MahbubHossainFaisal/Data_Engineering_Concepts/tree/main/Python_Package_Practice',
    packages=find_packages(),
    install_requires=[
        'pandas',
        'numpy',
        'matplotlib',
        'seaborn',
        'scikit-learn'
    ],
    classifiers=[
        'Programming Language :: Python :: 3',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
    ],
    python_requires='>=3.6',
)