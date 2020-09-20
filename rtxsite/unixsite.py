import os


def get_vitals():
    return (
        os.path.join(os.environ["HOME"], "work", "rtxlib"),
        os.path.join("/etc/rtx/config.ini"),
        None,
    )
