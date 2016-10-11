from setuptools import setup, find_packages


long_description = """\
Scan the wall schedule of FabLab Luxembourg and publish it online during open
access hours.
"""

setup(
    name="fablab_schedule",
    version="0.1.0",
    description="FabLab Luxembourg wall schedule scanner",
    long_description=long_description,
    url="http://github.com/asnt/fablablux-schedule",
    author="asnt",
    author_email="snt.alex@gmail.com",
    license="GPL",
    packages=find_packages(),
    package_data={
        "fablab_schedule": [
            "data/wall-reference.png",
            "data/wall-test.jpg",
            "conf/fablab_schedule.cfg.example",
        ],
    },
    entry_points = {
        "console_scripts": [
            "fablab_schedule_daemon=fablab_schedule.daemon:run",
            "fablab_schedule_scan=fablab_schedule.scanner:main",
        ]
    }
)
