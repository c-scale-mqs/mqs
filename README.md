# C-SCALE Metadata Query Service (MQS)

The MQS is a STAC-compliant FastAPI application and the central interface to query and identify Copernicus data distributed across partners within the C-SCALE data fedaration.
The present package is directly based on the [stac-fastapi](https://github.com/stac-utils/stac-fastapi) library.

## Installation

This package can be installed into a [conda](https://docs.conda.io/en/latest/miniconda.html) environment using the provided environment file.

```bash
# To install manually make sure to have miniconda installed!
git clone git@github.com:c-scale-mqs/mqs.git
cd mqs
conda create -y -f ./environment.yml

conda activate cscale-mqs
python setup.py install 
```

Or it can be built via the provided Dockerfile.

```bash
docker build -t eodc/mqs .
```

## Usage

The API can be started via

```bash
python -m mqs.app
```

Or via Docker, e.g. by using the provided docker-compose setup file:

```bash
docker-compose up
```

By default, the MQS exposes the API on port 80.


## Contributing
Contributions are welcome!

## License
[MIT](https://choosealicense.com/licenses/mit/)