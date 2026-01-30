#****************************************************************************
#* zsp_parser core.pxd
#****************************************************************************
cimport zsp_parser.decl as decl
cimport debug_mgr.core as dm_core
cimport zsp_parser.ast as ast
from libc.stdint cimport int32_t
from libcpp cimport bool

cdef class Factory(object):
    cdef decl.IFactory      *_hndl

    cpdef ast.Factory getAstFactory(self)

    cpdef dm_core.DebugMgr getDebugMgr(self)

    cpdef void loadStandardLibrary(self,
        AstBuilder          ast_builder,
        ast.GlobalScope     glbl_scope)

    cpdef LookupLocationResult lookupLocation(
        self,
        ast.RootSymbolScope     root,
        ast.Scope               scope,
        int                     lineno,
        int                     linepos)

    cpdef AstBuilder mkAstBuilder(self, MarkerListener marker_l)

    cpdef Linker mkAstLinker(self)

    cpdef SymbolTableIterator mkAstSymbolTableIterator(self,
        ast.SymbolScope     root)

    cpdef MarkerCollector mkMarkerCollector(self)

    cdef init(self, dm_core.Factory f, ast.Factory ast_f)

cdef Factory _factoryInst = None


cdef class AstBuilder(object):
    cdef decl.IAstBuilder      *_hndl

    cpdef build(self,
        ast.GlobalScope         root,
                                in_s)

    cpdef void setCollectDocStrings(self, bool collect)

    cpdef bool getCollectDocStrings(self)

    @staticmethod
    cdef AstBuilder mk(decl.IAstBuilder *hndl)

cdef class Linker(object):
    cdef decl.ILinker           *_hndl
    cdef bool                   _owned

    cpdef ast.RootSymbolScope link(self,
        MarkerListener         marker_l,
        scopes)

    @staticmethod
    cdef Linker mk(decl.ILinker *hndl, bool owned=*)

cdef class Location(object):
    cdef int32_t        _file
    cdef int32_t        _line
    cdef int32_t        _pos

cdef class LookupLocationResult(object):
    cdef decl.ILookupLocationResult     *_hndl
    cdef bool                           _owned

    @staticmethod
    cdef LookupLocationResult mk(decl.ILookupLocationResult *hndl, bool owned=*)

cdef class Marker(object):
    cdef decl.IMarker               *_hndl
    cdef bool                       _owned

    cpdef str msg(self)

    cpdef severity(self)

    cpdef Location loc(self)

    @staticmethod
    cdef Marker mk(decl.IMarker *hndl, bool owned=*)

cdef class MarkerListener(object):
    cdef decl.IMarkerListener       *_hndl
    cdef bool                       _owned

    cpdef bool hasSeverity(self, s)

cdef class MarkerCollector(MarkerListener):

    cpdef markers(self)

    cpdef int numMarkers(self)

    cpdef Marker getMarker(self, int idx)

    cdef decl.IMarkerCollector *asCollector(self)

    @staticmethod
    cdef MarkerCollector mk(decl.IMarkerCollector *hndl, bool owned=*)

cdef class SymbolTableIterator(object):
    cdef decl.ISymbolTableIterator  *_hndl
    cdef bool                       _owned

    @staticmethod
    cdef SymbolTableIterator mk(decl.ISymbolTableIterator *hndl, bool owned=*)

