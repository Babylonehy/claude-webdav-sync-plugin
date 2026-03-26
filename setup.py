from setuptools import setup, find_packages

setup(
    name="claude-webdav-sync",
    version="1.0.0",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    install_requires=[
        "webdavclient3>=3.14",
        "pyyaml>=6.0",
        "click>=8.0",
        "python-dateutil>=2.8",
    ],
    entry_points={
        "console_scripts": [
            "webdav-sync=webdav_sync.cli:main",
        ],
    },
)
