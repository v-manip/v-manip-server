

# copyright ...


class SceneRendererInterface(object):

	@property
	def formats(self):
		""" List of supported formats
		"""

	def render_scene(self, coverages, parameters):
		"""
		"""
