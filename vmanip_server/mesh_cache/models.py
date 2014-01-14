#-------------------------------------------------------------------------------
#
# Project: V-MANIP Server <http://v-manip.eox.at>
# Authors: Daniel Santillan <daniel.santillan@eox.at>
#
#-------------------------------------------------------------------------------
# Copyright (C) 2012 EOX IT Services GmbH
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


from django.db import models

class Layer(models.Model):
	name = models.CharField(max_length=256, unique=True)

	def __unicode__(self):
		return self.name

class TileLevel(models.Model):
	layer = models.ForeignKey(Layer)
	value = models.IntegerField()

	def __unicode__(self):
		return str(self.value) + ' of layer ' + self.layer.name

# TODO: not working
# class TileLevelAdmin(admin.ModelAdmin):
#     list_display = ('name',)
#     search_fields = ('layers__name',)

class TileCol(models.Model):
	tilelevel = models.ForeignKey(TileLevel)
	value = models.IntegerField()

	def __unicode__(self):
		return str(self.value) + ' of level ' + str(self.tilelevel.value) + ' of layer ' + str(self.tilelevel.layer.name)

class TileRow(models.Model):
	tilecol = models.ForeignKey(TileCol)
	value = models.IntegerField()
	content_file = models.CharField(max_length=256)

	def __unicode__(self):
		return str(self.value) + ' of level ' + str(self.tilecol.value) + ' of layer ' + self.tilecol.tilelevel.layer.name

