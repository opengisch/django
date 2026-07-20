ARG PYTHON_VERSION=3.13
ARG UV_VERSION=0.8.3
ARG GEOS_VERSION=3.14.1

FROM ghcr.io/astral-sh/uv:${UV_VERSION} AS uv

FROM python:${PYTHON_VERSION}-trixie

ARG GEOS_VERSION

ARG USER_ID=1001
ARG GROUP_ID=1001

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_CACHE_DIR=/home/django/.cache/uv \
    UV_PROJECT_ENVIRONMENT=/workspace/.venv \
    PATH="/workspace/.venv/bin:${PATH}"

RUN apt-get update \
    && apt-get install --yes --no-install-recommends \
        bash \
        build-essential \
        ca-certificates \
        bzip2 \
        cmake \
        curl \
        gdal-bin \
        gettext \
        git \
        libffi-dev \
        libgdal-dev \
        libgeos-dev \
        libjpeg62-turbo-dev \
        libmemcached-dev \
        libproj-dev \
        libsasl2-dev \
        libsqlite3-dev \
        libsqlite3-mod-spatialite \
        libssl-dev \
        libxml2-dev \
        libxslt1-dev \
        pkg-config \
        proj-bin \
        sqlite3 \
        zlib1g-dev \
    && rm -rf /var/lib/apt/lists/*

RUN curl --fail --location --silent --show-error \
        "https://download.osgeo.org/geos/geos-${GEOS_VERSION}.tar.bz2" \
        --output /tmp/geos.tar.bz2 \
    && tar --extract --bzip2 --file /tmp/geos.tar.bz2 --directory /tmp \
    && cmake \
        -S "/tmp/geos-${GEOS_VERSION}" \
        -B /tmp/geos-build \
        -DCMAKE_BUILD_TYPE=Release \
        -DCMAKE_INSTALL_PREFIX=/usr/local \
        -DBUILD_TESTING=OFF \
    && cmake --build /tmp/geos-build --parallel "$(nproc --all | awk '{print ($1 > 8) ? 8 : $1}')" \
    && cmake --install /tmp/geos-build \
    && ldconfig \
    && rm -rf /tmp/geos.tar.bz2 /tmp/geos-build "/tmp/geos-${GEOS_VERSION}"

COPY --from=uv /uv /uvx /usr/local/bin/

RUN groupadd --gid "${GROUP_ID}" django \
    && useradd \
        --uid "${USER_ID}" \
        --gid "${GROUP_ID}" \
        --create-home \
        --shell /bin/bash \
        django \
    && mkdir -p \
        /workspace \
        /workspace/.venv \
        /home/django/.cache/uv \
    && chown -R django:django \
        /workspace \
        /home/django

WORKDIR /workspace

COPY --chown=django:django docker/entrypoint.sh /usr/local/bin/django-entrypoint

RUN chmod 0755 /usr/local/bin/django-entrypoint

USER django

ENTRYPOINT ["django-entrypoint"]
CMD ["bash"]
