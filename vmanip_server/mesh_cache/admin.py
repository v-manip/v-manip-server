from django.contrib import admin
from vmanip_server.mesh_cache.models import (
	Layer, TileLevel, TileCol, TileRow
)

admin.site.register(Layer)
admin.site.register(TileLevel)
admin.site.register(TileCol)
admin.site.register(TileRow)