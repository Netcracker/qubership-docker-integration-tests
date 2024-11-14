import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="integration-tests-builtIn",
    version="0.1.17",
    author="framework_team",
    description="BuiltIn Robot Framework keywords source package",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/Netcracker/docker-integration-tests/integration-tests-built-in-library",
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.7',
)
