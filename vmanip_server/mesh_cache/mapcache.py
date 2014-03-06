from os.path import exists, basename, isfile
import sqlite3
from io import BytesIO
from datetime import datetime
import logging

from django.db import models as models
from django.db import connections

logger = logging.getLogger(__name__)

URN_TO_GRID = {
    "urn:ogc:def:wkss:OGC:1.0:GoogleMapsCompatible": "GoogleMapsCompatible",
    "urn:ogc:def:wkss:OGC:1.0:GoogleCRS84Quad": "WGS84"
}

class Connection(object):
    def handle(self, tileset, grid, dim, x, y, z, f):
        logger.info('[MapCache::handle]: Parameters: row: %s / col: %s / level: %s' % (x,y,z))

        db = self.opendb('/var/www/cache/%s.sqlite' % (tileset))
        logger.info('[MapCache::handle] Opened sqlite db: ' + '/var/www/cache/%s.sqlite' % (tileset))

        db.add_tile(tileset, grid, dim, x, y, z, f);
        logger.info('[MapCache::handle] Added tile.')

    def opendb(self, path, mode="r"):
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
    data = models.TextField() # TODO: wrapper for blob
    dim = models.TextField()
    ctime = models.DateTimeField()
    
    class Meta(object):
        db_table = "tiles"


def open_queryset(path):
    if not exists(path):
        raise TileSetException("TileSet '%s' does not exist.")
    
    name = basename(path)
    if not name in connections.databases:        
        connections.databases[name] = {
            "NAME": path,
            "ENGINE": "django.db.backends.sqlite3"
        }
        
    _ = connections[name]
    
    return TileModel.objects.using(name)

# end TODO

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
                        data blob,
                        dim text,
                        ctime datetime,
                        primary key(tileset,grid,x,y,z,dim)
                    );
                """)
            
    def get_tiles(self, tileset, grid, dim=None, minzoom=None, maxzoom=None):
        """ Generator function to loop over all tiles in a given zoom interval
        and a given dimension.
        """
        with sqlite3.connect(self.path) as connection:
            cur = connection.cursor()
            where_clauses = [
                "tiles.grid = '%s'" % grid,
                "tiles.tileset = '%s'" % tileset
            ]
            
            if minzoom is not None:
                where_clauses.append("tiles.z <= %d" % minzoom)
            
            if maxzoom is not None:
                where_clauses.append("tiles.z >= %d" % maxzoom)
                
            if dim:
                where_clauses.append("tiles.dim = '%s'" % dim)
            
            #rows = self.rows or "tileset, grid, x, y, z, dim, data"
            
            sql = ("SELECT tileset, grid, x, y, z, dim, data FROM tiles%s;" 
                   % (" WHERE " + " AND ".join(where_clauses) 
                      if len(where_clauses) else ""))
            
            cur.execute(sql)
            
            while True:
                row = cur.fetchone()
                if not row:
                    break
                
                yield row[:-1] + (BytesIO(row[-1]),)
    
    def add_tile(self, tileset, grid, dim, x, y, z, f):
        """ Add a new tile entry into the sqlite database file with the given
        values.
        """
        with sqlite3.connect(self.path) as connection:
            cur = connection.cursor()
            img_buffer = buffer(f.read())

            try:            
                cur.execute("INSERT INTO tiles VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                            (tileset, grid, x, y, z, img_buffer, dim, 
                             datetime.now()))
                connection.commit()
            except:
                logger.debug('Prevented duplicate tile from being inserted (source: database constraint)')
        
        

