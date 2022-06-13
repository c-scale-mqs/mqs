Features
========

**A concise overview of STAC-related features supported by the MQS.**

The MQS represents an implementation of a STAC-compliant API. As such, 
it can be used to *browse* and *search* dynamic STAC Catalogs. It is 
very recommended to familiarize oneself with the official 
`STAC API Specifications <https://github.com/radiantearth/stac-api-spec>`__ to 
get a good understanding of the basic concepts. Additionally, playing with 
the provided `implementation <https://stacspec.org/STAC-api.html>`__ will 
immediatlely help in getting a better feeling for the provided functionality.


Browse the MQS
--------------

The `MQS landing page <https://mqs.eodc.eu/stac/v1>`__ represents the entry 
point for users to browse the available Catalogs. It is itself a valid STAC 
Catalog containing links to Collections and other basic information. 

The MQS builds upon `FastAPI <https://fastapi.tiangolo.com/>`__, a simple 
framework for building web APIs. One of the benefits of FastAPI is the 
automatic generation of documentation via the Swagger software. Swagger 
is a useful tool for helping users to get started with the API. The MQS 
docs are available at 
`https://stac.eodc.eu/api/v1/docs <https://stac.eodc.eu/api/v1/docs>`__.

List all collections
~~~~~~~~~~~~~~~~~~~~

A first step in exploring the available datasets is checking out the Collections 
endpoint available at 
`https://mqs.eodc.eu/stac/v1/collections <https://mqs.eodc.eu/stac/v1/collections>`__. 
It returns a list of STAC Collections from various data providers within the 
C-SCALE federation.

List items of a Collection
~~~~~~~~~~~~~~~~~~~~~~~~~~

Make use of the items endpoint to look *inside* a specific STAC collection.
For instance, to fetch features for the Sentinel-1 GRD Collection hosted by
EODC, use the following link: `https://mqs.eodc.eu/stac/v1/collections/EODC|sentinel1-grd <https://mqs.eodc.eu/stac/v1/collections/EODC|sentinel1-grd>`__.

STAC Browser
~~~~~~~~~~~~

A great way of exploring STAC Catalogs is provided by the `STAC Browser <https://github.com/radiantearth/stac-browser>`__ utlity. 
It aims at providing a user-friendly and web-based visualization of STAC 
Catlogs directly within a web browser. 

Intended originally only for static Catalogs, i.e. purely JSON-file based 
without API functionality, the STAC Browser currently only provides minimal 
support for STAC APIs. Nonetheless, it already facilitates the discovery of
available datasets by presenting easily readable metadata and data previews.
For the MQS, the current version of the browser (v2.0.0) was installed and 
is available at `https://mqs.eodc.eu/browser <https://mqs.eodc.eu/browser>`__.

Note that for the next release of the software, the developers have promised
a significantly more sophistacted interface and better support for APIs.
Click 
`here <https://radiantearth.github.io/stac-browser/#/external/mqs.eodc.eu/stac/v1>`__ for a preview of this upcoming version of the STAC Browser 
displaying the MQS.


Search the MQS
--------------

The benefit of using dynamic STAC implementations of the STAC specifications 
is primarily given by the possibility to search the Catalog with an API.

There are many tools around for interacting with STAC APIs, tailored to 
facilitate the handling of STAC-specific objects like Collections 
or Items. Users can utilize these tools or choose any other software 
capable of working with HTTP APIs.

A good overview of available tools can be found on the `STAC Ecosystem <https://stacindex.org/ecosystem>`__ website.

Please note that the MQS currently only supports the **core parameters** for the 
STAC search. 

Those are:

- limit 
- bbox 
- datetime 
- intersects 
- ids 
- collections

See all details at the `STAC API spec github page 
<https://github.com/radiantearth/stac-api-spec/tree/master/item-search#query-parameter-table>`__.

With the CLI 
~~~~~~~~~~~~

For example, issue a POST request to the MQS search endpoint 
(`https://mqs.eodc.eu/stac/v1/search <https://mqs.eodc.eu/stac/v1/search>`__)
with cURL.


.. code-block:: bash
    
  curl --location --request POST 'https://mqs.eodc.eu/stac/v1/search' \
  --header 'Content-Type: application/json' \
  --data-raw '{
      "collections": [
          "EODC|sentinel1-grd"
      ],
      "datetime": "2022-04-01T00:00:00Z/.."
  }'


With Python
~~~~~~~~~~~

For example, use the 
`PySTAC Client <https://github.com/stac-utils/pystac-client>`__ 
in Python to interface with the MQS.


.. code-block:: python

   >>> from pystac_client import Client

   >>> mqs = Client.open("https://mqs.eodc.eu/stac/v1")

   >>> for collection in mqs.get_all_collections():
   ...     print(collection)
     
   <CollectionClient id=EODC|sentinel1-grd>
   <CollectionClient id=VITO|urn:eop:VITO:CGS_S1_GRD_L1>
   <CollectionClient id=VITO|urn:eop:VITO:CGS_S1_GRD_SIGMA0_L1>
   <CollectionClient id=VITO|urn:eop:VITO:CGS_S1_SLC_L1>
   <CollectionClient id=VITO|urn:eop:VITO:CGS_S2_L1C>
   <CollectionClient id=VITO|urn:eop:VITO:COP_DEM_GLO_30M_COG>
   <CollectionClient id=VITO|urn:eop:VITO:COP_DEM_GLO_90M_COG>
   <CollectionClient id=VITO|urn:eop:VITO:ESA_WorldCover_10m_2020_V1>
   <CollectionClient id=VITO|urn:eop:VITO:ESA_WorldCover_S1VVVHratio_10m_2020_V1>
   <CollectionClient id=VITO|urn:eop:VITO:ESA_WorldCover_S2RGBNIR_10m_2020_V1>
   <CollectionClient id=VITO|urn:eop:VITO:TERRASCOPE_S1_SLC_COHERENCE_V1>
   <CollectionClient id=VITO|urn:eop:VITO:TERRASCOPE_S2_CCC_V2>
   <CollectionClient id=VITO|urn:eop:VITO:TERRASCOPE_S2_CHL_V1>
   <CollectionClient id=VITO|urn:eop:VITO:TERRASCOPE_S2_CWC_V2>
   <CollectionClient id=VITO|urn:eop:VITO:TERRASCOPE_S2_FAPAR_V2>
   <CollectionClient id=VITO|urn:eop:VITO:TERRASCOPE_S2_FCOVER_V2>
   <CollectionClient id=VITO|urn:eop:VITO:TERRASCOPE_S2_LAI_V2>
   <CollectionClient id=VITO|urn:eop:VITO:TERRASCOPE_S2_NDVI_V2>
   <CollectionClient id=VITO|urn:eop:VITO:TERRASCOPE_S2_RHOW_V1>
   <CollectionClient id=VITO|urn:eop:VITO:TERRASCOPE_S2_SPM_V1>
   <CollectionClient id=VITO|urn:eop:VITO:TERRASCOPE_S2_TOC_V2>
   <CollectionClient id=VITO|urn:eop:VITO:TERRASCOPE_S2_TUR_V1>
   <CollectionClient id=VITO|urn:eop:VITO:TERRASCOPE_S5P_L3_CO_TD_V1>
   <CollectionClient id=VITO|urn:eop:VITO:TERRASCOPE_S5P_L3_CO_TM_V1>
   <CollectionClient id=VITO|urn:eop:VITO:TERRASCOPE_S5P_L3_CO_TY_V1>
   <CollectionClient id=VITO|urn:eop:VITO:TERRASCOPE_S5P_L3_NO2_TD_V1>
   <CollectionClient id=VITO|urn:eop:VITO:TERRASCOPE_S5P_L3_NO2_TM_V1>
   <CollectionClient id=VITO|urn:eop:VITO:TERRASCOPE_S5P_L3_NO2_TY_V1>
   <CollectionClient id=VITO|urn:ogc:def:EOP:VITO:PROBAV_S1-TOC_333M_V001>
   <CollectionClient id=VITO|urn:ogc:def:EOP:VITO:PROBAV_S10-TOC_333M_V001>
   <CollectionClient id=VITO|urn:ogc:def:EOP:VITO:PROBAV_S5-TOC_100M_V001>
   <CollectionClient id=VITO|urn:ogc:def:EOP:VITO:VGT_P>
   <CollectionClient id=VITO|urn:ogc:def:EOP:VITO:VGT_S1>
   <CollectionClient id=VITO|urn:ogc:def:EOP:VITO:VGT_S10>
   