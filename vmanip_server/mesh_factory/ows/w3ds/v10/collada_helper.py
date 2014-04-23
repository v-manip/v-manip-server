from collada import source, geometry, material, scene
import itertools
import numpy as np


class trianglestrip:
    def __init__(self):
        self._point_count = 0
        self.__coords = []
        self.__UVs = []
        self.__normals = []

    def add_point(self, coord, UV, normal):
        self._point_count += 1
        self.__coords.extend(coord)
        self.__UVs.extend(UV)
        self.__normals.extend(normal)

    def make_geometry(self, mesh, name, id, matnode):
        assert (self._point_count > 3)
        coords_name = name + "-verts-array"
        UVs_name = name + "-UVs-array"
        normals_name = name + "-normals-array"
        vert_src = source.FloatSource(coords_name, np.array(self.__coords), ('X', 'Y', 'Z'))
        UV_src = source.FloatSource(UVs_name, np.array(self.__UVs), ('U', 'V'))
        normal_src = source.FloatSource(normals_name, np.array(self.__normals), ('X', 'Y', 'Z'))
        geom = geometry.Geometry(mesh, name + "-geometry", 
                                 id, # use separate id for additional meta data (e.g. time)
                                 [vert_src, normal_src, UV_src])  # material overrides double_sided
        indices = []
        for p in xrange(3, self._point_count + 1):
            if (p % 2 == 1):
                indices.extend(xrange(p - 1, p - 4, -1))
            else:
                indices.extend(xrange(p - 3, p))
        indices = [val for val in indices for _ in xrange(0, 3)]
        input_list = source.InputList()
        input_list.addInput(0, 'VERTEX', "#" + coords_name)
        input_list.addInput(1, 'NORMAL', "#" + normals_name)
        input_list.addInput(2, 'TEXCOORD', "#" + UVs_name)
        triset = geom.createTriangleSet(np.array(indices), input_list, matnode.symbol)
        geom.primitives.append(triset)
        mesh.geometries.append(geom)
        geomnode = scene.GeometryNode(geom, [matnode])
        return geomnode


def make_emissive_material(mesh, name, texture_file_name):
    texture = material.CImage(name + "-texture", texture_file_name)
    mesh.images.append(texture)
    surf = material.Surface(name + "-surf", texture)
    sampler = material.Sampler2D(name + "-sampl", surf, minfilter="LINEAR_MIPMAP_LINEAR", magfilter="NONE")
    uvmap = material.Map(sampler, "TEXCOORD_0")
    effect = material.Effect(name + "-effect", [sampler, surf], "phong", diffuse=uvmap, emission=uvmap, double_sided=True)
    mat = material.Material(name + "-material", name, effect)
    mesh.effects.append(effect)
    mesh.materials.append(mat)
    return scene.MaterialNode(name, mat, inputs=[])
