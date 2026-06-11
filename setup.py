from setuptools import find_packages, setup


setup(
    name="mulearn-career-roadmap",
    version="0.1.0",
    description="Personalized career roadmap generator for Mulearn community members.",
    package_dir={"": "src"},
    packages=find_packages(where="src"),
    python_requires=">=3.10",
)
