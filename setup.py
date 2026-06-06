"""Legacy setuptools entry-point. Works standalone or with pyproject.toml."""

from setuptools import find_packages, setup

with open("README.md", encoding="utf-8") as f:
    long_description = f.read()

setup(
    name="imgoptimizer",
    version="0.1.0",
    description="A powerful image optimizer for web and storage. Resize, compress, and strip metadata.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="Your Name",
    author_email="your.email@example.com",
    license="MIT",
    python_requires=">=3.9",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    install_requires=[
        "Pillow>=10.0.0",
        "pillow-heif>=1.0.0",
        "typer>=0.12.0",
        "rich>=13.0.0",
        "piexif>=1.1.3",
    ],
    extras_require={
        "dev": [
            "pytest>=8.0.0",
            "pytest-cov>=4.0.0",
            "ruff>=0.4.0",
            "mypy>=1.10.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "imgoptimizer=imgoptimizer.cli:app",
        ],
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Multimedia :: Graphics",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
    keywords=["image", "optimization", "compression", "webp", "jpeg", "png", "gif", "heic", "svg", "cli"],
)
