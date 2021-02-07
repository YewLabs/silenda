FROM gcr.io/google-appengine/python

RUN apt-get update && apt-get install -y \
    software-properties-common apt-transport-https ca-certificates \
    && add-apt-repository ppa:jonathonf/gcc

RUN apt-get update && apt-get install -y \
    gcc-7 \
    g++-7 \
    build-essential \
    python-dev \
    python-pip \
    python3-dev \
    python3-pip \
    python3-venv \
    python3-setuptools \
    cmake \
    --no-install-recommends \
    && rm -rf /var/lib/apt/lists/*

RUN pip install cmake

# Create a virtualenv for dependencies. This isolates these packages from
# system-level packages.
# Use -p python3 or -p python3.7 to select python version. Default is version 2.
RUN virtualenv /env -p python3.7

# Setting these environment variables are the same as running
# source /env/bin/activate.
ENV VIRTUAL_ENV /env
ENV PATH /env/bin:$PATH

# Copy the application's requirements.txt and run pip to install all
# dependencies into the virtualenv.
ADD requirements.txt /app/requirements.txt
RUN pip install -r /app/requirements.txt

ADD libs/ /app/libs/

ENV CC /usr/bin/gcc-7
ENV CXX /usr/bin/g++-7

RUN pip install /app/libs/baba-is-auto

# Add the application source code.
ADD . /app

# Run a WSGI server to serve the application. gunicorn must be declared as
# a dependency in requirements.txt.
CMD daphne -b 0.0.0.0 -p $PORT silenda.asgi:application
