from setuptools import setup, find_packages

setup(
    name="li-post-engine",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "anthropic>=0.40.0",
        "cloudinary>=1.40.0",
        "requests>=2.32.0",
        "python-dotenv>=1.0.0",
        "schedule>=1.2.0",
        "tavily-python>=0.3.0",
        "pillow>=10.0.0",
        "jinja2>=3.1.0",
        "rich>=13.0.0",
        "click>=8.1.0",
        "httpx>=0.27.0",
    ],
    entry_points={
        "console_scripts": [
            "li-post=main:cli",
        ],
    },
    python_requires=">=3.11",
)
