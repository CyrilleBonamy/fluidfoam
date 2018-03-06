#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri Mar  2 17:58:06 2018

@author: mauriceg
"""

import unittest

import fluidfoam 
 
case = 'data/wingMotion2D_simpleFoam'


class SimpleTestCase(unittest.TestCase):
    def test_read_forces(self):
        postpro = fluidfoam.PostProFoamFile(case)
        postpro.readforces()
        self.assertEqual(1, len(postpro.forcedirs))
        print('create force object')
            
