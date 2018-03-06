#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Read OpenFoam Files for Python
===========================================
This module provides functions to read OpenFoam PostProcessing Files:

.autoclass:: PostProFoamFile

.. autofunction:: readforces

.autoclass:: Forcesfile

.. autofunction:: dumpdata

.. autofunction:: _parseforces


"""
import os 
from numpy import array,append

class PostProFoamFile(object):
    """ 
        class that contain all information you need to extract data
        from the postprocessing directory .
        usage :
            postpro=PostProFoamFile(case directory)
            will scan the postprocessing directory and create directory list
            that contain the forces directories, the probes directories,   
    """
    def __init__(self, case):
        try:
            L=os.listdir(os.path.join(case, 'postProcessing'))
            L=os.path.join(case, 'postProcessing')
        except OSError:
            print('no postprocessing in this case')
            print('nothing to do')
        self.direc=case   
        self.forcedirs=[]
        self.probesdirs=[]
        self.surfacesampledirs=[]
        for root, dirs, file in os.walk(L):
            if 'forces.dat' in file:
                self.forcedirs.append(root)
            if 'probes' in root.split('/')[0:-1]:
                self.probesdirs.append(root)
            if 'surfaceSampling' in root.split('/')[0:-1]:
                self.surfacesampledirs.append(root)
    
    
    def readforces(self):
        """
            function that scan the force directories 
            and create the force objects with the proper names and pathes
        """
        restartprev = '0'
        nrestart = 0
        objectlist = []
        for forcedir in self.forcedirs:
            ob = forcedir.split('/')[-2]
            restart = forcedir.split('/')[-1]
            if restart == '0':
                restartname = 'transit'
            elif float(restartprev) < float(restart):           
                nrestart += 1    
                restartname = 'restart'+str(nrestart)
            else:
                nrestart = 1
                restartname = 'restart'+str(nrestart)
                
            ### create force forcefiles object
            exec('self.' + ob+'_'+restartname+'='+ 'Forcesfile(forcedir)')
            objectlist.append(ob+'_'+restartname)
            print('create object:' + ob + restartname)
            restartprev = restart
        return objectlist
        
        

class Forcesfile(object):
    """ 
        class that  contain all information you need to extract data from the forcefile.
        Usage:
            ForceObject = Forcesfile(forcedirectory)
    """
    def __init__(self, forcedir):
        self.dir = forcedir
        self.starttime = float(forcedir.split('/')[-1])
        self.obj = forcedir.split('/')[-2]
        self.varlist = ['T','Fpx','Fpy','Fpz','Fvx','Fvy','Fvz'
                        ,'Fpox','Fpoy','Fpoz','Mpx','Mpy','Mpz'
                        ,'Mvx','Mvy','Mvz','Mpox','Mpoy','Mpoz']
                
    def _parse_forces(self,data):
        """ 
        function that parse the force file format
        """ 
        
        data = data.split('\n')
        header = data[0:3] #extract the header
        data_w = data[3:-1].copy()  # whole data
        tab = array([])
        for n,line in enumerate(data_w):
            line = line.replace('(','')
            line = line.replace(')','')
            line = line.split()            
            line = array(line,dtype=float)
            tab=append(tab,line)
        
        tab=tab.reshape((len(data_w),len(line)))
        print('***************************************************************')
        print('header for ',self.obj,'/',self.starttime,'/','forces.dat')
        for line in header:
            print(line)
        return tab
            
            
        
       
   
    def dumpdata(self):
        """ dump the data contained in the force file .
        create the forces variables in the Forcesfile object
        Args:
            no args
        Returns:
            .
        A way you might use me is:\n
        forceobject.dumpdata() will create and fill the force variables 
                        ['T','Fpx','Fpy','Fpz','Fvx','Fvy','Fvz'
                        ,'Fpox','Fpoy','Fpoz','Mpx','Mpy','Mpz'
                        ,'Mvx','Mvy','Mvz','Mpox','Mpoy','Mpoz']

        """
        with open(os.path.join(self.dir,'forces.dat'),'r') as f:
            data = f.read()
        
  
        tab = self._parse_forces(data)
        self.N_timestep = tab.shape[0]
        for n,var in enumerate(self.varlist):
            exec('self.'+ var +'=tab[:,' + str(n) + '].copy()' )
        
        
        
              
        
                    
                            
    
            
        
            
    
        
