# C-SCALE Metadata Query Service (MQS)

The MQS is a STAC-compliant FastAPI application and the central interface to query and identify Copernicus data distributed across partners within the C-SCALE data fedaration.
The present package is directly based on the [stac-fastapi](https://github.com/stac-utils/stac-fastapi) library.

## Installation and Deployment

### Overview

The package contains the following docker-compose files to allow for a quick deployment on any server.

- `docker-compose.traefik.yml`: sets up a Traefik instance and takes care about HTTPS certificates, reverse proxying and load balancing.
- `docker-compose.yml`: installs and starts the MQS app in a Docker container.

Note that the deployment setup is based on [tiangolo](https://github.com/tiangolo)'s guide on [how to deploy fastapi apps with https](https://dev.to/tiangolo/deploying-fastapi-and-other-apps-with-https-powered-by-traefik-5dik).

### Prerequesites

A working installation of [Docker](https://docs.docker.com/get-docker/) and [Docker Compose](https://docs.docker.com/compose/install/) is required.

Furthermore, the Docker network specified in the docker-compose files needs to be created before building the Docker containers. The exact command depends on your network infrastructure, but might be as simple as

```bash
docker network create mqs01
```

Additionally, the following environment variables need to be set:

```bash
# Traefik
USERNAME=                                          # Traefik Dashboard user name
PASSWORD=                                          # Traefik Dashboard password
HASHED_PASSWORD=$(openssl passwd -apr1 $PASSWORD)  # Hashed password created via openssl
EMAIL=                                             # Email to be registered with Let's Encrypt
DOCKER_IP_TRAEFIK=                                 # Docker IP assigned to the traefik service

# MQS App
MQS_HOST=                                          # will be used like this: https://{MQS_HOST}/stac/v1
MQS_PORT=                                          # port inside the container.
```

### Start the Stack

If all requirements are met, the Traefik and MQS containers can be started via `docker-compose up`:

```bash
docker-compose -f docker-compose.traefik.yml up -d
docker-compose -f docker-compose.yml up -d
```

The MQS app should then be available at `https://{MQS_HOST}/stac/v1`.

### Local Installation

This package can also be installed locally into a [conda](https://docs.conda.io/en/latest/miniconda.html) environment using the provided environment file.

```bash
# To install manually make sure to have miniconda installed!
git clone git@github.com:c-scale-mqs/mqs.git
cd mqs
conda env create -f ./environment.yml

conda activate cscale-mqs
pip install .
```

Or it can be built via the provided Dockerfile.

```bash
docker build -t eodc/mqs .
```

### Local Usage

The API can then be started via

```bash
python -m mqs.app
```

Or via Docker, e.g. by using the provided docker-compose setup file:

```bash
docker-compose up
```

By default, the MQS exposes the API on port 8000.

## Local Development

For local development, an override docker-compose file for the MQS is provided. The package will be installed in development mode inside the container and all code changes will be reflected without the need to re-build the image.

To get started use

```bash
docker-compose up --build
```

without the `-f` option!

## Whitelisting Non-GOCDB Sites

In this project, a YAML configuration file is used to manage whitelisted and blacklisted data providers. This configuration provides control over which providers to include or exclude in the application.

### YAML Configuration

The YAML configuration file, typically named `data_providers.yaml`, has the following structure:

```yaml
# Sample YAML configuration for data providers

whitelist:
  - provider1
  - provider2

blacklist:
  - provider3
  - provider4

data_providers:
  - identifier: provider1
    name: Provider 1
    stac_url: https://provider1.com/api/stac
    limit: 100

  # Add more data providers as needed
```

* `whitelist`: Contains identifiers of white-listed data providers.
* `blacklist`: Contains identifiers of black-listed data providers. Can refer to GOCDB sites as well.
* `data_providers`: Contains information about each data provider, including their identifier, name, STAC URL, and limit.

### Including in Docker Compose

To use this configuration in Docker Compose, the YAML file can be mounted into the desired location within the container. Additionally, you can define an environment variable to specify the location of the configuration file.

Here's an example of how to modify the Docker Compose file to include the configuration:

```yaml
version: '3'
services:
  backend:
    environment:
      - DATA_PROVIDERS_CONFIG_FILE_PATH=/path/to/config.yaml  # Set the desired path
    volumes:
      - ./config.yaml:/path/to/config.yaml

```

Replace `backend` with the name of the service and adjust the other configuration details accordingly. In this example, the `DATA_PROVIDERS_CONFIG_FILE_PATH` environment variable is used to define the location of the configuration file within the container.

If the environment variable is not specified, the default location for the configuration file is assumed to be `/opt/data_providers.yaml`.

Ensure that the application reads the configuration from the specified path, either the one defined by the environment variable or the default path, within the container to utilize the whitelisting and blacklisting functionality effectively.

## Testing

The tests inside the MQS container started in development mode can be executed via

```bash
docker exec MQS_CONTAINER_NAME pytest
```

where MQS_CONTAINER_NAME needs to be replaced with the actual name of the running container.

## Contributing

Contributions are welcome!

## License

[MIT](https://choosealicense.com/licenses/mit/)
