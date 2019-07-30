from setuptools import setup, find_packages

version = "0.1.0"
setup(
    name="gitdump",
    version=version,
    description="A tool to get the data from github and store it in mongodb",
    keywords="gitdump",
    install_requires=[
        "PyGithub==1.36",
        "pymongo==2.7.2",
        "tornado==4.5.3",
        "basescript==0.2.0",
        "deeputil==0.2.5",
        "gnsq==0.4.0",
    ],
    package_dir={"gitdump": "gitdump"},
    packages=find_packages("."),
    include_package_data=True,
    classifiers=[
        "Programming Language :: Python :: 2.7",
        "Environment :: Console",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
    ],
    test_suite="test.suitefn",
    entry_points={"console_scripts": ["gitdump = gitdump:main"]},
)
