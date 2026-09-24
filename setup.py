from setuptools import setup

setup(
    name="envdiff",
    version="1.0.0",
    description="Compare environment-file keys without exposing values",
    long_description=open("README.md", "r", encoding="utf-8").read(),
    long_description_content_type="text/markdown",
    author="Michael Kandziora",
    url="https://github.com/michaelkandziora/shell.envdiff",
    license="MIT",
    package_dir={"": "src"},
    packages=["envdiff"],
    python_requires=">=3.6",
    entry_points={"console_scripts": ["envdiff=envdiff.cli:main"]},
    classifiers=[
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3 :: Only",
        "License :: OSI Approved :: MIT License",
    ],
)
