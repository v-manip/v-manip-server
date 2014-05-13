import nibabel as nib
import numpy as np
from osgeo import gdal, gdalconst, osr

from eoxserver.resources.coverages import crss

def convert_GeoTIFF_2_NiFTi(coverage, in_fname, out_fname, bbox, crs):


    srid = crss.parseEPSGCode(crs, (crss.fromShortCode, crss.fromURN, crss.fromURL))

    dataset = gdal.Open(in_fname, gdalconst.GA_ReadOnly)

    in_sr = osr.SpatialReference()
    in_sr.ImportFromEPSG(4326) # TODO: get real projection value
    out_sr = osr.SpatialReference()
    out_sr.ImportFromEPSG(srid)

    if not in_sr.IsSame(out_sr):

        raise Exception(dataset.GetProjection())
        ct = osr.CoordinateTransformation(out_sr, in_sr)
        p0 = ct.TransformPoint(bbox[0], bbox[1])
        p1 = ct.TransformPoint(bbox[2], bbox[3])
        #TODO


    gt = dataset.GetGeoTransform()

    #origin x, offset x1, offset y1, origin y, offset x2, offset y2

    image_bbox = coverage.footprint.extent
    res_x, res_y = coverage.resolution


    bbox[0] = max(image_bbox[0], bbox[0])
    bbox[1] = max(image_bbox[1], bbox[1])
    bbox[2] = min(image_bbox[2], bbox[2])
    bbox[3] = min(image_bbox[3], bbox[3])

    r = (
        int((bbox[0] - image_bbox[0]) / res_x),
        int((bbox[1] - image_bbox[1]) / res_y),
        int((bbox[2] - image_bbox[0]) / res_x),
        int((bbox[3] - image_bbox[1]) / res_y)
    )

    from ngeo_browse_server.config import models
    layer = models.Browse.objects.get(coverage_id=coverage.identifier).browse_layer
    layer.radiometric_interval_min

    volume = np.array(dataset.GetRasterBand(1).ReadAsArray(r[0], r[1], r[2]-r[0], r[3]-r[1]))
    for i in range(2, dataset.RasterCount+1):
        volume=np.dstack((volume, dataset.GetRasterBand(i).ReadAsArray(r[0], r[1], r[2]-r[0], r[3]-r[1])))

    volume = np.clip(volume, layer.radiometric_interval_min, layer.radiometric_interval_max)

    img = nib.Nifti1Image(volume, np.eye(4))
    img.to_filename(out_fname)

