import nibabel as nib
import numpy as np
from osgeo import gdal
from osgeo import gdalconst

def convert_GeoTIFF_2_NiFTi(in_fname, out_fname):

    dataset = gdal.Open(in_fname, gdalconst.GA_ReadOnly)

    volumen = np.array(dataset.GetRasterBand(1).ReadAsArray())
    for i in range(2, dataset.RasterCount+1):
        volumen=np.dstack((volumen, dataset.GetRasterBand(i).ReadAsArray()))

    img = nib.Nifti1Image(volumen, np.eye(4))
    img.to_filename(out_fname)

