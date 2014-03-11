#-------------------------------------------------------------------------------
#
# Project: V-MANIP Server <http://v-manip.eox.at>
# Authors: Martin Hecher <martin.hecher@fraunhofer.at>
#
#-------------------------------------------------------------------------------
# Copyright (C) 2014 Fraunhofer Austria GmbH
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies of this Software or works derived from this Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
#-------------------------------------------------------------------------------


from os.path import isfile
import sqlite3
# from io import BytesIO
from datetime import datetime
import logging
from django.db import models as models


logger = logging.getLogger(__name__)


URN_TO_GRID = {
    "urn:ogc:def:wkss:OGC:1.0:GoogleMapsCompatible": "GoogleMapsCompatible",
    "urn:ogc:def:wkss:OGC:1.0:GoogleCRS84Quad": "WGS84"
}


class MapCacheSQLite(object):
    def __init__(self, db_folder):
        self.db_folder = db_folder

    def store(self, tileset, grid, z, x, y, dim, tilesets):
        logger.info('[MapCacheSQLite::store] Processing %s tilesets ...' % (len(tilesets),))
        tile_geo = None

        # For now we have pairs of tilesets, consisting of a W3DS and a corresponding WMTS entry:
        for item in tilesets:
            # logger.debug('[MapCacheSQLite::store] Tileset data %s' % (item,))

            path = '%s/%s.sqlite' % (self.db_folder, tileset)
            db = self.connect(path)
            logger.debug('[MapCacheSQLite::handle] Opened sqlite db: ' + self.db_folder + '/%s.sqlite' % (tileset))

            # NOTE: see http://gis.stackexchange.com/questions/3334/what-is-the-difference-between-wgs84-and-epsg4326
            # for the 'difference' between the identifiers (TLDR: there is none in our case)
            if grid == 'WGS84':
                grid = 'EPSG:4326'

            if item['protocol'].upper() == 'W3DS':
                db.add_w3ds_tile(tileset, grid, dim, x, y, z, item['json'])
                # FIXXME!
                tile_geo = item['json']
            # else:
                # db.add_wmts_tile(tileset, grid, dim, x, y, z, item['data'])

            logger.info('[MapCacheSQLite::handle] Processed %s tile ...' % item['protocol'].upper())

        return tile_geo

    def lookup(self, tileset, grid, z, x, y, dim):
        path = '%s/%s.sqlite' % (self.db_folder, tileset)
        db = self.connect(path)
        logger.debug('[MapCacheSQLite::handle] Opened sqlite db: ' + self.db_folder + '/%s.sqlite' % (tileset))

        # NOTE: see http://gis.stackexchange.com/questions/3334/what-is-the-difference-between-wgs84-and-epsg4326
        # for the 'difference' between the identifiers (TLDR: there is none in our case)
        if grid == 'WGS84':
            grid = 'EPSG:4326'

        return db.get_tile(tileset, grid, dim, x, y, z)

    def connect(self, path, mode="r"):
        db_exists = isfile(path)
        create = False

        if not db_exists and mode == "r":
            raise TileSetException("TileSet '%s' does not exist." % path)
        elif not db_exists and mode == "w":
            create = True

        # TODO: schema detection
        # SELECT name FROM sqlite_master WHERE type = 'table';
        # TODO: other schemas
        return SQLiteSchemaTileSet(path, create)


# Django does not support multi-column primary keys
class TileModel(models.Model):
    tileset = models.TextField()
    grid = models.TextField()
    x = models.IntegerField()
    y = models.IntegerField()
    z = models.IntegerField()
    data = models.TextField()  # TODO: wrapper for blob
    dim = models.TextField()
    ctime = models.DateTimeField()

    class Meta(object):
        db_table = "tiles"


# def open_queryset(path):
#     if not exists(path):
#         raise TileSetException("TileSet '%s' does not exist.")

#     name = basename(path)
#     if not name in connections.databases:
#         connections.databases[name] = {
#             "NAME": path,
#             "ENGINE": "django.db.backends.sqlite3"
#         }

#     _ = connections[name]

#     return TileModel.objects.using(name)

# # end TODO


class TileSetException(Exception):
    pass


class SQLiteSchemaTileSet(object):
    def __init__(self, path, create=False):
        self.path = path

        if create:
            with sqlite3.connect(path) as connection:
                cur = connection.cursor()
                cur.executescript("""\
                    create table if not exists tiles(
                        tileset text,
                        grid text,
                        x integer,
                        y integer,
                        z integer,
                        data text,
                        dim text,
                        ctime datetime,
                        primary key(tileset,grid,x,y,z,dim)
                    );
                """)

    def add_wmts_tile(self, tileset, grid, dim, x, y, z, data_json):
        """ Add a new tile entry into the sqlite database file with the given
        values.
        """
        with sqlite3.connect(self.path) as connection:
            cur = connection.cursor()

            try:
                cur.execute("INSERT INTO tiles VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                            (tileset, grid, x, y, z, 'blablub', dim,
                             datetime.now()))
                connection.commit()
            except:
                logger.debug('Prevented duplicate tile from being inserted')

            return data_json

    def add_w3ds_tile(self, tileset, grid, dim, x, y, z, f):
        """ Add a new tile entry into the sqlite database file with the given
        values.
        """
        with sqlite3.connect(self.path) as connection:
            cur = connection.cursor()
            # img_buffer = buffer(f.read())
            json = f

            # print 'insert json:\n' + str(json)
            try:
                cur.execute("INSERT INTO tiles VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                            # (tileset, grid, x, y, z, str(json.replace('"path": "', '"path": "http://localhost:3080/gltf/')), dim,
                            (tileset, grid, x, y, z, str(json), dim,
                             datetime.now()))
                connection.commit()
            except:
                logger.debug('Prevented duplicate tile from being inserted')

            return json

    def get_tile(self, tileset, grid, dim, x, y, z):
        """ Returns the tile data for the given parameters. If no tile is stored
        'None' is returned.
        """
        with sqlite3.connect(self.path) as connection:
            cur = connection.cursor()
            where_clauses = [
                "tiles.tileset = '%s'" % tileset,
                "tiles.grid = '%s'" % grid,
                # "tiles.dim = '%s'" % dim,
                "tiles.x = '%s'" % x,
                "tiles.y = '%s'" % y,
                "tiles.z = '%s'" % z
            ]

            sql = ("SELECT data FROM tiles%s;"
                   % (" WHERE " + " AND ".join(where_clauses)
                      if len(where_clauses) else ""))

            # print('sql: ', sql)

            cur.execute(sql)

            row = cur.fetchone()

            if row:
                # print('data: ', row[0])
                return row[0]
            else:
                return None
