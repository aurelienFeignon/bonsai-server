# Runtime officiel PrismML pour les formats natifs Bonsai (Q1_0/PQ2_0/PTQ1_0), isolé des autres services GPU.
ARG CUDA_BASE_IMAGE=nvidia/cuda:12.8.1-runtime-ubuntu24.04
FROM ${CUDA_BASE_IMAGE}
RUN apt-get update \
 && apt-get install -y --no-install-recommends ca-certificates curl libgomp1 libcurl4t64 \
 && rm -rf /var/lib/apt/lists/*
WORKDIR /opt/bonsai
ARG LLAMA_RELEASE=prism-b10777-e3de715
ARG LLAMA_CUDA_VERSION=12.8
ARG LLAMA_ARCHIVE_SHA256=aa53e2256276e683386effdc8be34b3bd1cdf64ef9dc5d492da69227ac52531b
RUN curl --fail --location --retry 3 \
      "https://github.com/PrismML-Eng/llama.cpp/releases/download/${LLAMA_RELEASE}/llama-${LLAMA_RELEASE}-bin-linux-cuda-${LLAMA_CUDA_VERSION}-x64.tar.gz" \
      -o /tmp/llama.tar.gz \
 && echo "${LLAMA_ARCHIVE_SHA256}  /tmp/llama.tar.gz" | sha256sum -c - \
 && tar -xzf /tmp/llama.tar.gz --strip-components=1 \
 && rm /tmp/llama.tar.gz
ENV LD_LIBRARY_PATH=/opt/bonsai:/usr/local/cuda/lib64
COPY docker/entrypoint.sh /usr/local/bin/bonsai-entrypoint
RUN chmod +x /usr/local/bin/bonsai-entrypoint
ENTRYPOINT ["/usr/local/bin/bonsai-entrypoint"]
