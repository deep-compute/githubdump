import doctest
import unittest

from gitdump import githubhistory

def suitefn():
    suite = unittest.TestSuite()
    suite.addTests(doctest.DocTestSuite(githubhistory))
    return suite

if __name__ == "__main__":
    doctest.testmod(githubhistory)
