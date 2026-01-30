import unittest
from zuspec.fe.pss import Parser
from zuspec.fe.pss.core import Factory
from zuspec.fe.pss.utils import *

class TestParser(unittest.TestCase):
    
    def test_smoke(self):
        factory = Factory.inst()
#        factory.getDebugMgr().enable(True)
        parser = Parser()

        parser.parses([
            ("abc.pss", """
             component C {}
             component pss_top {
                action A { }
             }
             """),
            ("def.pss", """
component X {
//    D d1;
}
             """),
        ])

        sym_tree_root = parser.link()

        if sym_tree_root.symtabHas("pss_top"):
            print("Found", flush=True)
            pss_top_i = sym_tree_root.symtabAt("pss_top")
            print("pss_top_i: %d" % pss_top_i)
            pss_top = sym_tree_root.getChild(pss_top_i)
            print("pss_top: %s" % str(pss_top))
            print("post-pss_top", flush=True)
            if pss_top.symtabHas("A"):
                print("Has A", flush=True)
#                A = pss_top.symtabAt("A")
            else:
                print("No A", flush=True)
        else:
            print("Didn't Find")
        
        sym_tree_root_u = SymbolScopeUtil(sym_tree_root)
        for c in sym_tree_root.children():
            print("Child: %s" % (c.getName() if hasattr(c, "getName") else str(c)))
        
        A = sym_tree_root_u.getQname("pss_top::A")
        print("A: %s" % str(A))
        pass

    def test_inheritance(self):
        factory = Factory.inst()
#        factory.getDebugMgr().enable(True)
        parser = Parser()

        parser.parses([
            ("abc.pss", """
             component C {}
             component pss_top {
                action A { }

                action B : A { }
             }
             """),
        ])

        sym_tree_root_u = SymbolScopeUtil(parser.link())
        
        A = SymbolTypeScopeUtil(sym_tree_root_u.getQname("pss_top::A"))
        print("A: %s" % str(A))
        A_super = A.getSuper()
        print("A_super: %s" % str(A_super))
        assert A_super is None

        B = SymbolTypeScopeUtil(sym_tree_root_u.getQname("pss_top::B"))
        B_super = B.getSuper()
        print("B_super: %s" % str(B_super))
        assert B_super is not None
        assert B_super.getName() == "A"

    def test_extension(self):
        factory = Factory.inst()
        factory.getDebugMgr().enable(True)
        parser = Parser()

        parser.parses([
            ("abc.pss", """
             component C {}
             component pss_top {
                action A { }
             }

             extend component pss_top {
                action B : A { }
             }
             """),
        ])

        sym_tree_root_u = SymbolScopeUtil(parser.link())
        
        A = SymbolTypeScopeUtil(sym_tree_root_u.getQname("pss_top::A"))
        print("A: %s" % str(A))
        A_super = A.getSuper()
        print("A_super: %s" % str(A_super))
        assert A_super is None

        B = SymbolTypeScopeUtil(sym_tree_root_u.getQname("pss_top::B"))
        B_super = B.getSuper()
        print("B_super: %s" % str(B_super))
        assert B_super is not None
        assert B_super.getName() == "A"

        pass

    def test_extension_s(self):
        factory = Factory.inst()
        factory.getDebugMgr().enable(True)
        parser = Parser()

        parser.parses([
            ("abc.pss", """
             component C {}
             component pss_top {
                action A { }
             }

             extend component pss_top {
                action B : A { }
             }

             extend component pss_top {
                action C : A { }
             }
             """),
        ])

        sym_tree_root_u = SymbolScopeUtil(parser.link())

        pss_top_u = SymbolScopeUtil(sym_tree_root_u.getQname("pss_top"))
        extensions = pss_top_u.getExtensions()
        print("extension: %s" % str(extensions))

        pass