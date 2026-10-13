import os

from test_sqlite import *  # noqa: F403

DATABASES["default"].update(  # noqa: F405
    {
        "ENGINE": "django.contrib.gis.db.backends.postgis",
        "NAME": os.environ.get("POSTGIS_NAME", "geodjango"),
        "USER": os.environ.get("POSTGIS_USER", "django"),
        "PASSWORD": os.environ.get("POSTGIS_PASSWORD", "django"),
        "HOST": os.environ.get("POSTGIS_HOST", "postgis"),
        "PORT": os.environ.get("POSTGIS_PORT", "5432"),
    }
)
DATABASES["other"].update(  # noqa: F405
    {
        "ENGINE": "django.contrib.gis.db.backends.postgis",
        "NAME": "geodjango2",
        "USER": os.environ.get("POSTGIS_USER", "django"),
        "PASSWORD": os.environ.get("POSTGIS_PASSWORD", "django"),
        "HOST": os.environ.get("POSTGIS_HOST", "postgis"),
        "PORT": os.environ.get("POSTGIS_PORT", "5432"),
    }
)
