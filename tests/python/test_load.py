'''
Created on Mar 24, 2021

@author: mballance
'''
from unittest.case import TestCase
from _io import StringIO
import zuspec.fe.pss.ast as zsp_ast

class TestLoad(TestCase):

    def foo(self):
        f = zsp_ast.Factory()
    
    def test_smoke(self):
        from zuspec.fe.pss import core as zspp_core
        from zuspec.fe.pss import ast as zspp_ast

        factory = zspp_core.Factory.inst()
        
        marker_l = factory.mkMarkerCollector()
        
        parser = factory.mkAstBuilder(marker_l)
        linker = factory.mkAstLinker()
        ast_f = factory.getAstFactory()

        glbl = ast_f.mkGlobalScope(0)
#        factory.loadStandardLibrary(parser, glbl)

        input = StringIO(
            """
             component pss_top {
             }

            """)
        print("--> parse")
        parser.build(glbl, input)
        print("<-- parse")
        self.assertFalse(marker_l.hasSeverity(zspp_core.MarkerSeverityE.Error))        

        print("--> link")
        linked = linker.link(marker_l, [glbl])
        print("<-- link")

        class ComponentCollector(zspp_ast.VisitorBase):

            def __init__(self):
                super().__init__()
                self.components = []

            def visitSymbolScope(self, s):
                print("visitSymbolScope")
                super().visitSymbolScope(s)

            def visitSymbolTypeScope(self, s):
                print("visitSymbolTypeScope")
                super().visitSymbolTypeScope(s)
#                s.getTarget().accept(self)

            def visitComponent(self, c):
                print("Component")
                super().visitComponent(c)
                self.components.append(c)

            def visitSymbolImportSpec(self, i):
                super().visitSymbolImportSpec(i)
                print("visitSymbolImportSpec")

#        print("linked=%s children=%d" % (str(linked), linked.getChildren().size()))

        v = ComponentCollector()
#        for m in dir(v):
#            print("Element: %s" % str(m))

        linked.accept(v)

        print("Components: %s" % str(v.components))

        self.assertFalse(marker_l.hasSeverity(zspp_core.MarkerSeverityE.Error))        

#        pssparser.core.doit(2)