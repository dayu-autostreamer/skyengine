FROM nvidia/cuda:11.8.0-devel-ubuntu22.04

ARG DEBIAN_FRONTEND=noninteractive
ARG PYTHON_VERSION=3.8

RUN apt-get update && \
  DEBIAN_FRONTEND=noninteractive apt-get -qq -y install \
  software-properties-common \
  libsm6 \
  libxext6 \
  build-essential \
  curl \
  cmake \
  g++ \
  ffmpeg \
  git \
  vim \
  nano \
  rsync \
  wget \
  unzip \
  libboost-all-dev \
  && apt-get clean \
  && rm -rf /var/lib/apt/lists/*

  RUN wget https://github.com/microsoft/onnxruntime/releases/download/v1.14.1/onnxruntime-linux-x64-1.14.1.tgz \
      && tar -xf onnxruntime-linux-x64-1.14.1.tgz \
      && cp onnxruntime-linux-x64-1.14.1/lib/* /usr/lib/ && cp onnxruntime-linux-x64-1.14.1/include/* /usr/include/
      
  # Clean up APT when done.
  RUN apt-get clean && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

  RUN add-apt-repository ppa:deadsnakes/ppa
  RUN apt-get update && apt-get install -y -qq python${PYTHON_VERSION} \
      python${PYTHON_VERSION}-dev \
      python${PYTHON_VERSION}-distutils \
      python${PYTHON_VERSION}-tk \
      && apt-get clean \
      && rm -rf /var/lib/apt/lists/*

# Set python aliases
RUN update-alternatives --install /usr/bin/python python /usr/bin/python${PYTHON_VERSION} 1
RUN update-alternatives --install /usr/bin/python3 python3 /usr/bin/python${PYTHON_VERSION} 1
RUN curl https://bootstrap.pypa.io/get-pip.py -o get-pip.py && python get-pip.py

ADD requirements.txt /tmp/

RUN pip install --no-cache-dir -r /tmp/requirements.txt && \
    pip install typing-extensions==4.5.0 && \
    pip install setuptools==69.5.1 && \
    rm -rf /tmp/* /var/tmp/* 
