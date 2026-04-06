from setuptools import setup, find_packages

setup(
    name="easy_core",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "pillow",
        "opencv-python",
        "numpy",
        "pypdfium2",
        "pyzbar"
    ],
    description="Noyau commun pour le traitement d'images et PDF pour EasyTess",
)
