"""Read OpenFoam Files for Python
===========================================
This module provides functions to list and read OpenFoam PostProcessing Files:

.. autofunction:: readforce

"""
import os
import numpy as np 

def varinforce():
    """ return the var included in postProcessing force files."""

    return ['T', 'Fpx', 'Fpy', 'Fpz', 'Fvx', 'Fvy', 'Fvz', 'Fpox',
                 'Fpoy', 'Fpoz', 'Mpx', 'Mpy', 'Mpz', 'Mvx', 'Mvy', 'Mvz',
                 'Mpox','Mpoy','Mpoz']

def readforce(path, namepatch='forces', time_name='0', name='forces'):
    """ read the data contained in the force file .
    create the forces variables in the Forcesfile object

    Args:
        path: str\n
        time_name: str\n
        name: str

    Returns:
        array: array of force field; size of the array is the size of the
    time

    A way you might use me is:\n
    force = readforce('path_of_OpenFoam_case', '0', 'forces')\n
    It will create and fill the force variables 
                    ['T','Fpx','Fpy','Fpz','Fvx','Fvy','Fvz'
                    ,'Fpox','Fpoy','Fpoz','Mpx','Mpy','Mpz'
                    ,'Mvx','Mvy','Mvz','Mpox','Mpoy','Mpoz']

    """

    with open(os.path.join(path, 'postProcessing', namepatch, time_name,
                           name+'.dat'),'rb') as f:
        content = f.read()
    data = content.split(b'\n')
    j = 0
    header = True
    for i, line in enumerate(data[:-1]):
        if '#'.encode() in line:
            j += 1
        elif '#'.encode() not in line and header==True:
            header = False
            line = line.replace(b'(', b'')
            line = line.replace(b')', b'')
            line = line.split()
            tab = np.zeros([len(data)-j-1, len(line)], dtype=float)
            j = 0
            tab[j, :] = np.array(line, dtype=float)
        else:
            j += 1
            line = line.replace(b'(', b'')
            line = line.replace(b')', b'')
            line = line.split()
            tab[j, :] = np.array(line, dtype=float)
    return tab
