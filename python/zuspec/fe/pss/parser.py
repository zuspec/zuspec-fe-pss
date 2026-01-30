from io import StringIO
from typing import Dict, List, Tuple, TextIO

class ParseException(Exception):
    pass

class Parser(object):

    def __init__(self):
        import zuspec.fe.pss.core as zspp
        import zuspec.fe.pss.ast as zsp_ast
        self.ast_f = zsp_ast.Factory.inst()
        self.parser_f = zspp.Factory.inst()
        self._root = None
        self._filenames : Dict[int,str] = {}
        self._files : List[zsp_ast.GlobalScope] = []
        pass

    def parse(self, files : List[str]) -> bool:
        import zuspec.fe.pss.core as zspp
        marker_l = self.parser_f.mkMarkerCollector()
        builder = self.parser_f.mkAstBuilder(marker_l)

        file_id = 0
        if len(self._files) == 0:
            stdlib = self.ast_f.mkGlobalScope(len(self._files()))
            self.parser_f.loadStandardLibrary(builder, stdlib)
            self._files.append(stdlib)

        for f in files:
            id = len(self._files)
            self._filenames[id] = f
            with open(f, "r") as fp:
                ast = self.ast_f.mkGlobalScope(id)
                builder.build(ast, fp)
            
            if marker_l.hasSeverity(zspp.MarkerSeverityE.Error):
                err = self._mkErrorMessage(marker_l)
                raise ParseException(err)

            self._files.append(ast)

        return True

    def parses(self, files : List[Tuple[str, str]]) -> bool:
        import zuspec.fe.pss.core as zspp
        marker_l = self.parser_f.mkMarkerCollector()
        builder = self.parser_f.mkAstBuilder(marker_l)

        if len(self._files) == 0:
            stdlib = self.ast_f.mkGlobalScope(len(self._files))
            self.parser_f.loadStandardLibrary(builder, stdlib)
            self._files.append(stdlib)

        for fname,fstr in files:
            id = len(self._files)
            self._filenames[id] = fname
            ast = self.ast_f.mkGlobalScope(id)
            builder.build(ast, StringIO(fstr))
            
            if marker_l.hasSeverity(zspp.MarkerSeverityE.Error):
                err = self._mkErrorMessage(marker_l)
                raise ParseException(err)

            self._files.append(ast)

        return True
    
    def link(self) -> 'zsp_ast.RootSymbolScope':
        import zuspec.fe.pss.core as zspp
        linker = self.parser_f.mkAstLinker()
        marker_l = self.parser_f.mkMarkerCollector()

        ret = linker.link(marker_l, self._files)

        if marker_l.hasSeverity(zspp.MarkerSeverityE.Error):
            err = self._mkErrorMessage(marker_l)
            raise ParseException(err)

        self._filenames.clear()
        self._files.clear()
        
        return ret


    def _mkErrorMessage(self, marker_l) -> str:
        import zuspec.fe.pss.core as zspp
        prefix = {
            zspp.MarkerSeverityE.Error : "Error: ",
            zspp.MarkerSeverityE.Warn : "Warning: ",
            zspp.MarkerSeverityE.Info : "Info: ",
            zspp.MarkerSeverityE.Hint : "Hint: ",
        }
        msg = ""
        for i in range(marker_l.numMarkers()):
            marker = marker_l.getMarker(i)
            loc = marker.loc()
            marker_m = "%s%s %s:%d:%d" % (
                prefix[int(marker.severity())],
                marker.msg(),
                self._filenames[loc.file],
                loc.line,
                loc.pos+1)
            print(marker_m)
            msg += marker_m + "\n"

        return msg

    @property
    def root(self) -> 'zsp_ast.RootSymbolScope':
        return self._root
