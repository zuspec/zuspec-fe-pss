

cimport debug_mgr.decl as dm
from libcpp.pair cimport pair as cpp_pair
from libcpp.set cimport set as cpp_set
from libcpp.string cimport string as cpp_string
from libcpp.vector cimport vector as cpp_vector
from libcpp.memory cimport unique_ptr
from libc.stdint cimport intptr_t
from libc.stdint cimport int32_t
from libc.stdint cimport uint32_t
from libc.stdint cimport uint64_t
from libc.stdint cimport int64_t
from libcpp cimport bool
cimport cpython.ref as cpy_ref
from zsp_parser cimport ast_decl as ast
from ciostream.core cimport istream

ctypedef IFactory *IFactoryP
ctypedef IMarker *IMarkerP
ctypedef IMarkerCollector *IMarkerCollectorP
ctypedef unique_ptr[IMarker] IMarkerUP


cdef extern from "zsp/parser/IFactory.h" namespace "zsp::parser":
    cdef cppclass IFactory:

        void init(dm.IDebugMgr *dmgr, ast.IFactory *ast_factory)

        ast.IFactory *getAstFactory()

        dm.IDebugMgr *getDebugMgr()

        void loadStandardLibrary(
            IAstBuilder             *ast_builder,
            ast.IGlobalScope        *glbl_scope)

        ILookupLocationResult *lookupLocation(
            ast.IRootSymbolScope    *root,
            ast.IScope              *scope,
            int                     lineno,
            int                     linepos
        )

        IAstBuilder *mkAstBuilder(IMarkerListener *)

        ILinker *mkAstLinker()

        ISymbolTableIterator *mkAstSymbolTableIterator(
            ast.ISymbolScope        *root)

        IMarkerCollector *mkMarkerCollector()


cdef extern from "zsp/parser/IAstBuilder.h" namespace "zsp::parser":
    cdef cppclass IAstBuilder:

        void build(
            ast.IGlobalScope        *scope,
            istream                 *in_s)

        void setCollectDocStrings(bool)

        bool getCollectDocStrings()

cdef extern from "zsp/parser/ILinker.h" namespace "zsp::parser":
    cdef cppclass ILinker:

        ast.IRootSymbolScope *link(
            IMarkerListener         *marker_l,
            const cpp_vector[ast.IGlobalScopeP] &scopes)

        pass

cdef extern from "zsp/parser/ILookupLocationResult.h" namespace "zsp::parser":
    cdef cppclass ILookupLocationResult:
        pass

cdef extern from "zsp/parser/IMarker.h" namespace "zsp::parser":
    cdef enum MarkerSeverityE:
        Severity_Error "zsp::parser::MarkerSeverityE::Error"
        Severity_Warn "zsp::parser::MarkerSeverityE::Warn"
        Severity_Info "zsp::parser::MarkerSeverityE::Info"
        Severity_Hint "zsp::parser::MarkerSeverityE::Hint"
        Severity_NumLevels "zsp::parser::MarkerSeverityE::NumLevels"

    cdef cppclass IMarker:
        const cpp_string &msg() const
        MarkerSeverityE severity() const
        const ast.Location &loc() const;
        IMarker *clone() const

cdef extern from "zsp/parser/IMarkerListener.h" namespace "zsp::parser":
    cdef cppclass IMarkerListener:
        void marker(const IMarker *m)
        bool hasSeverity(MarkerSeverityE s)

cdef extern from "zsp/parser/IMarkerCollector.h" namespace "zsp::parser":
    cdef cppclass IMarkerCollector(IMarkerListener):
        const cpp_vector[IMarkerUP] &markers() const

cdef extern from "zsp/parser/ISymbolTableIterator.h" namespace "zsp::parser":
    cdef cppclass ISymbolTableIterator:
        int32_t findLocalSymbol(const cpp_string &name)

cdef extern from "PyParserUtils.h" namespace "zsp::parser":
    ast.IScopeChild *resolveSymbolPathRef "zsp::parser::PyParserUtils::resolveSymbolPathRef" (
        dm.IDebugMgr                *dmgr,
        ast.ISymbolChildrenScope    *root,
        const ast.ISymbolRefPath    *ref)
