import unittest

import fluidfoam 
 
case = 'output_samples/ascii'


class SimpleTestCase(unittest.TestCase):
    def test_read_forces(self):
        forces = fluidfoam.readforce(case)
        #self.assertEqual(1, len(postpro.forcedirs))
        print('create force object')
            
