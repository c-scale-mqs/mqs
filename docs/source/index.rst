.. mqs documentation master file, created by
   sphinx-quickstart on Fri Jun 10 11:36:43 2022.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

.. role:: raw-html(raw)
    :format: html

C-SCALE Metadata Query Service (MQS)
====================================

**The MQS is a STAC-compliant FastAPI application and the central
interface to query and identify Copernicus data distributed across
partners within the C-SCALE data federation.**


The service is hosted within the C-SCALE federated cloud infrastructure 
and is intended to provide a unified way of discovering 
Copernicus data available within the federation by making use of the 
`SpatioTemporal Asset Catalog (STAC) <https://stacspec.org/>`__ specification. 

For the end-user, there is **no need to install** this package 
on their machine. Instead, the service endpoint (`https://mqs.eodc.eu/stac/v1 
<https://mqs.eodc.eu/stac/v1>`__) can be accessed and interfaced with like 
any other STAC API. 
A growing list of software packages and tools to interact with 
STAC APIs supporting various programming languages can be found on 
the `STAC Ecosystem <https://stacindex.org/ecosystem>`__ website.

A good starting point for getting acquainted with the MQS and the STAC Catalogs available 
through the MQS is the STAC Browser: `https://mqs.eodc.eu/browser <https://mqs.eodc.eu/browser>`__. 

More information about C-SCALE, the contributing data providers and 
available datasets can be found on 
the `C-SCALE Wiki <https://wiki.c-scale.eu/C-SCALE>`__.


Example
-------

Use `PySTAC Client <https://github.com/stac-utils/pystac-client>`__ in Python to search 
for Sentinel-1 GRD data.


.. code-block:: python

   >>> from pystac_client import Client

   >>> mqs = Client.open("https://mqs.eodc.eu/stac/v1")

   >>> search_results = mqs.search(
   ...     collections=["sentinel1-grd",
   ...                  "urn:eop:VITO:CGS_S1_GRD_L1"],
   ...     bbox=[9.5,46.0,48.5,49.5],                               
   ...     datetime=['2022-01-01T00:00:00Z', '2022-06-01T00:00:00Z'],
   ...     max_items=5
   ... )
   
   >>> for item in search_results.items():
   ...     print(item.id)

   S1A_IW_GRDH_1SDV_20220101T164242_20220101T164307_041270_04E7B4_21E3
   S1A_IW_GRDH_1SDV_20220101T164217_20220101T164242_041270_04E7B4_DF08
   S1A_IW_GRDH_1SDV_20220101T150441_20220101T150506_041269_04E7AC_1A46
   S1A_IW_GRDH_1SDV_20220101T053511_20220101T053536_041263_04E777_374B
   S1A_IW_GRDH_1SDV_20220101T053446_20220101T053511_041263_04E777_3E25   

License
-------

`MIT <https://choosealicense.com/licenses/mit/>`__   


.. toctree::
   :maxdepth: 2
   :caption: Contents:

   features
   dataaccess
   install