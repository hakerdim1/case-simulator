FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive
ENV USER="user"
ENV HOME_DIR="/home/${USER}"
ENV WORK_DIR="${HOME_DIR}/hostcwd"
ENV PATH="${HOME_DIR}/.local/bin:${PATH}"

# Устанавливаем локаль
RUN apt-get update -qq && \
    apt-get install -y -qq --no-install-recommends locales && \
    locale-gen en_US.UTF-8
ENV LANG="en_US.UTF-8" LANGUAGE="en_US.UTF-8" LC_ALL="en_US.UTF-8"

# Устанавливаем системные зависимости для сборки
RUN apt-get update -qq && \
    apt-get install -y -qq --no-install-recommends \
    autoconf \
    automake \
    build-essential \
    ccache \
    cmake \
    gettext \
    git \
    libffi-dev \
    libltdl-dev \
    libssl-dev \
    libtool \
    openjdk-17-jdk \
    patch \
    pkg-config \
    python3-pip \
    python3-setuptools \
    python3-venv \
    sudo \
    unzip \
    zip \
    zlib1g-dev \
    libncurses5-dev \
    libncursesw5-dev \
    libtinfo5

# Создаем пользователя и виртуальное окружение
RUN useradd -m -s /bin/bash ${USER} && \
    echo "${USER} ALL=(ALL) NOPASSWD:ALL" >> /etc/sudoers
USER ${USER}
WORKDIR ${HOME_DIR}

RUN python3 -m venv .venv
ENV VIRTUAL_ENV="${HOME_DIR}/.venv"
ENV PATH="${VIRTUAL_ENV}/bin:${PATH}"

# Устанавливаем Buildozer и Cython (важно: Cython < 3.0)
RUN pip install --upgrade pip wheel && \
    pip install "cython<3.0" buildozer

WORKDIR ${WORK_DIR}
ENTRYPOINT ["buildozer"]
