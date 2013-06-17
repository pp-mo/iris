'''
Created on May 8, 2013

@author: itpp

Speed-test profiling tester
'''


import test_sphtrig_noniris as tsn

def testit():
    t = tsn.TestPolySpeed('test_speedrun')
    t()

if __name__ == '__main__':
    import cProfile
    cProfile.run('testit()', './poly_speed.prof')
    import pstats
    p = pstats.Stats('./poly_speed.prof')
    p.sort_stats('cumulative').print_stats(20)
