from setuptools import setup, find_packages

setup(
    name="agentx",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "click>=8.0.0",
        "pyyaml>=6.0.0",
        "pydantic>=2.0.0",
        "structlog>=24.1.0",
        "aiohttp>=3.9.0",
        "beautifulsoup4>=4.12.0",
        "pytest>=8.0.0",
        "pytest-asyncio>=0.23.0"
    ],
    python_requires=">=3.10",
)