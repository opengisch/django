ARG PYTHON_VERSION=3.13
ARG UV_VERSION=0.8.3

FROM ghcr.io/astral-sh/uv:${UV_VERSION} AS uv

FROM python:${PYTHON_VERSION}-bookworm

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
        gettext \
        git \
        libffi-dev \
        libjpeg62-turbo-dev \
        libmemcached-dev \
        libsasl2-dev \
        libsqlite3-dev \
        libssl-dev \
        libxml2-dev \
        libxslt1-dev \
        pkg-config \
        sqlite3 \
        zlib1g-dev \
    && rm -rf /var/lib/apt/lists/*

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
