from setuptools import setup, find_packages

setup(
    name="site-sentry",
    version="1.0.0",
    description="Autonomous website maintenance agent — Lighthouse audit → LLM fixes → GitHub PR",
    author="Rajat Balyan",
    packages=find_packages(),
    python_requires=">=3.10",
    entry_points={
        "console_scripts": [
            "sentry=site_sentry.cli.commands:cli",
        ],
    },
    install_requires=[
        "click>=8.1.0",
        "pyyaml>=6.0.0",
        "pydantic>=2.5.0",
        "structlog>=24.1.0",
        "python-dotenv>=1.0.0",
        "langchain>=0.3.0",
        "langchain-core>=0.3.0",
        "langchain-openai>=0.2.0",
        "langgraph>=0.2.0",
        "openai>=1.30.0",
        "beautifulsoup4>=4.12.0",
        "requests>=2.31.0",
        "aiohttp>=3.9.0",
        "gitpython>=3.1.40",
        "chromadb>=0.5.0",
    ],
    extras_require={
        "google": ["langchain-google-genai>=2.0.0"],
        "groq": ["langchain-groq>=0.2.0"],
        "dev": ["pytest>=8.0.0", "pytest-asyncio>=0.23.0"],
    },
)
