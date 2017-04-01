from setuptools import setup

setup(
    name="envdiff",
    version="0.2.0",
    description="Compare environment-file keys without exposing values",
    long_description=open("README.md", "r", encoding="utf-8").read(),
    long_description_content_type="text/markdown",
    author="Michael Kandziora",
    author_email="michael@kandziora.local",
    url="https://example.invalid/envdiff",
    license="MIT",
    package_dir={"": "src"},
    packages=["envdiff"],
    python_requires=">=3.6",
    entry_points={"console_scripts": ["envdiff=envdiff.cli:main"]},
    classifiers=[
        "Programming Language :: Python :: 3.6",
        "License :: OSI Approved :: MIT License",
    ],
)
