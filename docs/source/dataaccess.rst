Data Access
===========

**Example usages to search and use metadata to access data via the MQS.**

Please note that this is still work in progress.

Assets 
~~~~~~

STAC Items usually contain links to assets like preview images, metadata files 
and to the actual data products. This can be handled by each data provider 
individually.
An example to search for files within the EODC cloud environment and to use 
the actual data is shown below:


.. code-block:: python

   >>> from pystac_client import Client

   >>> mqs = Client.open("https://mqs.eodc.eu/stac/v1")

   >>> search_results = mqs.search(
   ...     collections=["EODC|sentinel1-grd"], 
   ...     bbox=[9.5,46.0,48.5,49.5], 
   ...     datetime=['2022-01-01T00:00:00Z', '2022-06-01T00:00:00Z'], 
   ...     max_items=5)

   >>> for item in search_results.items():
   ...     zip_file = item.assets['safe-zip'].extra_fields['alternate']['local']['href']
   ...     thumbnail_full = item.assets['thumbnail'].extra_fields['alternate']['local']['href']
   ...     thumbnail_rel = thumbnail_full.split(zip_file)[1][1:]
   ...     print(zip_file)
   ...     print(thumbnail_full)
   ...     print(thumbnail_rel)

   /eodc/products/copernicus.eu/s1a_csar_grdh_iw/2022/01/01/S1A_IW_GRDH_1SDV_20220101T164242_20220101T164307_041270_04E7B4_21E3.zip
   /eodc/products/copernicus.eu/s1a_csar_grdh_iw/2022/01/01/S1A_IW_GRDH_1SDV_20220101T164242_20220101T164307_041270_04E7B4_21E3.zip/S1A_IW_GRDH_1SDV_20220101T164242_20220101T164307_041270_04E7B4_21E3.SAFE/preview/quick-look.png
   S1A_IW_GRDH_1SDV_20220101T164242_20220101T164307_041270_04E7B4_21E3.SAFE/preview/quick-look.png
   /eodc/products/copernicus.eu/s1a_csar_grdh_iw/2022/01/01/S1A_IW_GRDH_1SDV_20220101T164217_20220101T164242_041270_04E7B4_DF08.zip
   /eodc/products/copernicus.eu/s1a_csar_grdh_iw/2022/01/01/S1A_IW_GRDH_1SDV_20220101T164217_20220101T164242_041270_04E7B4_DF08.zip/S1A_IW_GRDH_1SDV_20220101T164217_20220101T164242_041270_04E7B4_DF08.SAFE/preview/quick-look.png
   S1A_IW_GRDH_1SDV_20220101T164217_20220101T164242_041270_04E7B4_DF08.SAFE/preview/quick-look.png
   /eodc/products/copernicus.eu/s1a_csar_grdh_iw/2022/01/01/S1A_IW_GRDH_1SDV_20220101T150441_20220101T150506_041269_04E7AC_1A46.zip
   /eodc/products/copernicus.eu/s1a_csar_grdh_iw/2022/01/01/S1A_IW_GRDH_1SDV_20220101T150441_20220101T150506_041269_04E7AC_1A46.zip/S1A_IW_GRDH_1SDV_20220101T150441_20220101T150506_041269_04E7AC_1A46.SAFE/preview/quick-look.png
   S1A_IW_GRDH_1SDV_20220101T150441_20220101T150506_041269_04E7AC_1A46.SAFE/preview/quick-look.png
   /eodc/products/copernicus.eu/s1a_csar_grdh_iw/2022/01/01/S1A_IW_GRDH_1SDV_20220101T053511_20220101T053536_041263_04E777_374B.zip
   /eodc/products/copernicus.eu/s1a_csar_grdh_iw/2022/01/01/S1A_IW_GRDH_1SDV_20220101T053511_20220101T053536_041263_04E777_374B.zip/S1A_IW_GRDH_1SDV_20220101T053511_20220101T053536_041263_04E777_374B.SAFE/preview/quick-look.png
   S1A_IW_GRDH_1SDV_20220101T053511_20220101T053536_041263_04E777_374B.SAFE/preview/quick-look.png
   /eodc/products/copernicus.eu/s1a_csar_grdh_iw/2022/01/01/S1A_IW_GRDH_1SDV_20220101T053446_20220101T053511_041263_04E777_3E25.zip
   /eodc/products/copernicus.eu/s1a_csar_grdh_iw/2022/01/01/S1A_IW_GRDH_1SDV_20220101T053446_20220101T053511_041263_04E777_3E25.zip/S1A_IW_GRDH_1SDV_20220101T053446_20220101T053511_041263_04E777_3E25.SAFE/preview/quick-look.png
   S1A_IW_GRDH_1SDV_20220101T053446_20220101T053511_041263_04E777_3E25.SAFE/preview/quick-look.png

   # work with ZIP archive e.g. using `zipfile <https://docs.python.org/3/library/zipfile.html>`__.
   

HTTP(S) Access
~~~~~~~~~~~~~~

It will also be possible to directly access assets via the web. 
The example above makes use of the alternate assets provided for 
EODC data access from e.g. VMs within the cloud.

The default asset href points to a server that provides access to the 
individual assets via HTTP. 

Example: `https://stac.eodc.eu/data/collections/sentinel1-grd/items/S1A_IW_GRDH_1SDV_20220101T053446_20220101T053511_041263_04E777_3E25/thumbnail <https://stac.eodc.eu/data/collections/sentinel1-grd/items/S1A_IW_GRDH_1SDV_20220101T053446_20220101T053511_041263_04E777_3E25/thumbnail>`__.

