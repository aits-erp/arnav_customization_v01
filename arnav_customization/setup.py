from setuptools import setup, find_packages

with open("requirements.txt") as f:
    requirements = f.read().splitlines()

setup(
    name="arnav_customization",
    version="0.0.1",
    description="many fields and doctypes with custom modifications",
    author="aits",
    author_email="nikhil@aitsind.com",
    packages=find_packages(),
    include_package_data=True,
    zip_safe=False,
    install_requires=requirements,
)