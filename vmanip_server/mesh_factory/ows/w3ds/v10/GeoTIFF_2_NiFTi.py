import random
import math
import nibabel as nib
import numpy as np
from osgeo import gdal, gdalconst, osr

from eoxserver.core.util.rect import Rect
from eoxserver.resources.coverages import crss
from eoxserver.contrib.vrt import VRTBuilder

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


    #gt = dataset.GetGeoTransform()

    #origin x, offset x1, offset y1, origin y, offset x2, offset y2

    image_bbox = coverage.footprint.extent
    res_x = (image_bbox[2] - image_bbox[0]) / dataset.RasterXSize
    res_y = (image_bbox[1] - image_bbox[3]) / dataset.RasterYSize


    bbox[0] = max(image_bbox[0], bbox[0])
    bbox[1] = max(image_bbox[1], bbox[1])
    bbox[2] = min(image_bbox[2], bbox[2])
    bbox[3] = min(image_bbox[3], bbox[3])


    r = (
        int( math.floor((bbox[0] - image_bbox[0]) / res_x) ),
        int( math.floor((bbox[3] - image_bbox[3]) / res_y) ),
        int( math.ceil((bbox[2] - image_bbox[0]) / res_x) ),
        int( math.ceil((bbox[1] - image_bbox[3]) / res_y) )
    )


    from ngeo_browse_server.config import models

    layer = models.Browse.objects.get(coverage_id=coverage.identifier).browse_layer

    if ('GOME-2' in coverage.identifier or 'NPL3Merged' in coverage.identifier or 'BASCOE' in coverage.identifier or 'LPL2_MIPAS' in coverage.identifier):
        scale = 1000000
        scale_y = res_y
        scale_x = res_x
        scale_z = 5
    else:
        scale = 1
        scale_y = res_y*200
        scale_x = res_x*200
        scale_z = 5


    if 'GOME-2' in coverage.identifier:
        layers = [3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16]
        volume = np.array(dataset.GetRasterBand(2).ReadAsArray(r[0], r[1], r[2]-r[0], r[3]-r[1])*scale )
        for i in layers:
            volume=np.dstack((volume, dataset.GetRasterBand(i).ReadAsArray(r[0], r[1], r[2]-r[0], r[3]-r[1])*scale ))
    
    elif 'BASCOE' in coverage.identifier:
        layers = [9, 13, 17, 19, 21, 24, 27, 28, 29, 31, 33, 34, 35, 37]
        volume = np.array(dataset.GetRasterBand(4).ReadAsArray(r[0], r[1], r[2]-r[0], r[3]-r[1])*scale )
        for i in layers:
            volume=np.dstack((volume, dataset.GetRasterBand(i).ReadAsArray(r[0], r[1], r[2]-r[0], r[3]-r[1])*scale ))

    else:
        volume = np.array(dataset.GetRasterBand(1).ReadAsArray(r[0], r[1], r[2]-r[0], r[3]-r[1])*scale )
        for i in range(2, dataset.RasterCount+1):
            volume=np.dstack((volume, dataset.GetRasterBand(i).ReadAsArray(r[0], r[1], r[2]-r[0], r[3]-r[1])*scale ))

    
    


    volume = np.clip(volume, layer.radiometric_interval_min, layer.radiometric_interval_max)

    offset = random.uniform(0.00000000000000, 0.00000000000001)

    scale = np.array([scale_y+offset,scale_x+offset,scale_z+offset,1])
    affine = np.diag(scale)
    img = nib.Nifti1Image(volume, affine)

    #img = nib.Nifti1Image(volume, np.eye(4))
    img.to_filename(out_fname)



def convert_collection_GeoTIFF_2_NiFTi (coverage_collection, out_fname, bbox, crs):

    srid = crss.parseEPSGCode(crs, (crss.fromShortCode, crss.fromURN, crss.fromURL))

    raster_collection = []

    dataset = gdal.Open(coverage_collection[0][1], gdalconst.GA_ReadOnly)
    image_bbox = coverage_collection[0][0].footprint.extent
    res_x = (image_bbox[2] - image_bbox[0]) / dataset.RasterXSize
    res_y = (image_bbox[1] - image_bbox[3]) / dataset.RasterYSize

    size_x = abs(int((bbox[2]-bbox[0])/res_x))
    size_y = abs(int((bbox[3]-bbox[1])/res_y))


    builder = VRTBuilder(size_x, size_y, len(coverage_collection), coverage_collection[0][0].range_type.bands.all()[0].data_type)

    for i, (coverage, in_fname) in enumerate(coverage_collection, start=1):
        
        dataset = gdal.Open(str(in_fname), gdalconst.GA_ReadOnly)

        in_sr = osr.SpatialReference()
        in_sr.ImportFromEPSG(4326) # TODO: get real projection value
        out_sr = osr.SpatialReference()
        out_sr.ImportFromEPSG(srid)

        if not in_sr.IsSame(out_sr):

            raise Exception(dataset.GetProjection())
            ct = osr.CoordinateTransformation(out_sr, in_sr)
            p0 = ct.TransformPoint(bbox[0], bbox[1])
            p1 = ct.TransformPoint(bbox[2], bbox[3])

        image_bbox = coverage.footprint.extent
        res_x = abs(image_bbox[2] - image_bbox[0]) / dataset.RasterXSize
        res_y = abs(image_bbox[1] - image_bbox[3]) / dataset.RasterYSize


        dst_rect = (
            int( math.floor((image_bbox[0] - bbox[0]) / res_x) ), # x offset
            int( math.floor((bbox[3] - image_bbox[3]) / res_y) ), # y offset
            dataset.RasterXSize, # x size
            dataset.RasterYSize  # y size
        )


        builder.add_simple_source(i, str(in_fname), 1, src_rect=(0, 0, dataset.RasterXSize, dataset.RasterYSize), dst_rect=dst_rect)


    volume = builder.dataset.GetRasterBand(1).ReadAsArray()
    for i in range(2, len(coverage_collection) + 1):
        volume = np.dstack((volume, builder.dataset.GetRasterBand(i).ReadAsArray()))


    offset = random.uniform(0.00000000000000, 0.00000000000001)

    scale = np.array([res_y*800+offset,res_x*800+offset,res_x*2400+offset,1])   
    affine = np.diag(scale)
    img = nib.Nifti1Image(volume, affine)
    
    #img = nib.Nifti1Image(volume, np.eye(4))
    img.to_filename(out_fname)