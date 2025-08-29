from setuptools import setup, find_packages

with open("requirements.txt") as f:
    install_requires = f.read().strip().split("\n")

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
