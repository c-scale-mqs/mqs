
# Image
FROM continuumio/miniconda3:4.10.3-alpine AS build

ARG version
ARG build_date

ENV PYTHONDONTWRITEBYTECODE=true
ENV PYTHONUNBUFFERED=true

# Labels
LABEL org.label-schema.schema-version="1.0"
LABEL org.label-schema.build-date=$build_date
LABEL org.label-schema.name="C-SCALE MQS"
LABEL org.label-schema.description="MQS is a package to search and identify Copernicus data across partners within the C-CALE data federation."
LABEL org.label-schema.url=""
LABEL org.label-schema.vcs-url=""
LABEL org.label-schema.vcs-ref=""
LABEL org.label-schema.vendor="EODC Gmbh (support@eodc.eu)"
LABEL org.label-schema.version=$version
LABEL org.label-schema.docker.cmd=""

# Add package
ADD . /mqs
WORKDIR /mqs

# Create environment, install dependencies and package
RUN conda config --set always_yes yes && \
    conda config --append channels conda-forge && \
    conda update -n base -c conda-forge conda && \
    conda env create -f ./environment.yml && \
    source activate cscale-mqs && \
    pip install . && \
    conda deactivate && \
    conda install -c conda-forge conda-pack && \
    conda clean -ity

# Use conda pack for multi-staging
RUN conda-pack -n cscale-mqs -o /tmp/env.tar && \
    mkdir /cscale-mqs && cd /cscale-mqs && tar xf /tmp/env.tar && \
    rm /tmp/env.tar

RUN /cscale-mqs/bin/conda-unpack

FROM debian:buster-slim AS runtime

COPY --from=build /cscale-mqs /cscale-mqs

RUN echo "source /cscale-mqs/bin/activate" > ~/.bashrc
ENV PATH="/cscale-mqs/bin:$PATH"

SHELL ["/bin/bash", "-c"]
