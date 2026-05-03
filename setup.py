from setuptools import setup, find_packages

setup(
    name="queryshield",
    version="3.0.0",
    packages=["queryshield", "queryshield.api", "queryshield.app", "queryshield.core", "queryshield.evaluation", "queryshield.retrieval"],
    package_dir={
        "queryshield": ".",
    },
)
