"""
Read and Plot a contour of OpenFoam output from a structured mesh
=================================================================

This example reads and plots a contour of the first component of an OpenFoam
vector field from a structured mesh
"""

###############################################################################
# First reads the mesh
# --------------------
#
# .. note:: It reads the mesh coordinates for a structured mesh (argument True)
#           and stores them in variables x, y and z

# import readmesh function from fluidfoam package
from fluidfoam import readmesh


sol = '../output_samples/box/'

x, y, z = readmesh(sol, True)

###############################################################################
# Reads a vector field
# --------------------
#
# .. note:: It reads a vector field from a structured mesh
#           and stores it in vel variable

# import readvector function from fluidfoam package
from fluidfoam import readvector

sol = '../output_samples/box/'
timename = '0'
vel = readvector(sol, timename, 'U', True)

###############################################################################
# Now plots the contour of the first velocity component at a given z position
# ---------------------------------------------------------------------------
# 

import matplotlib.pyplot as plt

plt.figure()
plt.contourf(x[:, :, 0], y[:, :, 0], vel[0, :, :, 0])
