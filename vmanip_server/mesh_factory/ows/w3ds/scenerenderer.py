




class X3DSceneRenderer(Component):
	implements(SceneRendererInterface)

	formats = ["x3d", "application/x3d"]

	def render_scene(self, coverages, parameters):

		scene = Scene()
		for coverage in coverages:
            # transform data to mesh
            mesh = Mesh(coverage)
            # add mesh to "scene"
            scene.append(mesh)

        return self.encode_x3d(scene)