from setuptools import setup, find_packages

try:
    with open("requirements.txt") as f:
        install_requires = [line.strip() for line in f if line.strip() and not line.startswith("#")]
except FileNotFoundError:
    install_requires = []

setup(
    name="crm",
    version="1.0.0",
    description="Kick-ass Open Source CRM",
    author="Frappe Technologies Pvt. Ltd.",
    author_email="shariq@frappe.io",
    packages=find_packages(),
    zip_safe=False,
    include_package_data=True,
    install_requires=install_requires,
)
