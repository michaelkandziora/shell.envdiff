from setuptools import setup

setup(
    name="envdiff",
    version="0.1.0",
    description="Compare environment-file keys without exposing values",
    package_dir={"": "src"},
    packages=["envdiff"],
    entry_points={"console_scripts": ["envdiff=envdiff.cli:main"]},
)
