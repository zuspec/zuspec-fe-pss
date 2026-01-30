# cython: language_level=3
from enum import IntEnum
from libcpp.cast cimport dynamic_cast
from libcpp.cast cimport reinterpret_cast
from libcpp.cast cimport static_cast
from libcpp.string cimport string as      std_string
from libcpp.map cimport map as            std_map
from libcpp.unordered_map cimport unordered_map as  std_unordered_map
from libcpp.memory cimport unique_ptr, shared_ptr
from libcpp.vector cimport vector as std_vector
from libcpp.utility cimport pair as  std_pair
from libcpp cimport bool as          bool
cimport cpython.ref as cpy_ref
from cython.operator cimport dereference

cdef extern from "zsp/ast/impl/UP.h" namespace "zsp::ast":
    cpdef cppclass UP[T](unique_ptr[T]):
        UP()
        UP(T *, bool)
        T *get()

ctypedef char                 int8_t
ctypedef unsigned char        uint8_t
ctypedef short                int16_t
ctypedef unsigned short       uint16_t
ctypedef int                  int32_t
ctypedef unsigned int         uint32_t
ctypedef long long            int64_t
ctypedef unsigned long long   uint64_t

ctypedef IRefExpr *IRefExprP
ctypedef UP[IRefExpr] IRefExprUP
ctypedef IExprAggrMapElem *IExprAggrMapElemP
ctypedef UP[IExprAggrMapElem] IExprAggrMapElemUP
ctypedef IMonitorActivitySelectBranch *IMonitorActivitySelectBranchP
ctypedef UP[IMonitorActivitySelectBranch] IMonitorActivitySelectBranchUP
ctypedef IExprAggrStructElem *IExprAggrStructElemP
ctypedef UP[IExprAggrStructElem] IExprAggrStructElemUP
ctypedef IScopeChild *IScopeChildP
ctypedef UP[IScopeChild] IScopeChildUP
ctypedef IActivityJoinSpec *IActivityJoinSpecP
ctypedef UP[IActivityJoinSpec] IActivityJoinSpecUP
ctypedef ISymbolImportSpec *ISymbolImportSpecP
ctypedef UP[ISymbolImportSpec] ISymbolImportSpecUP
ctypedef ISymbolRefPath *ISymbolRefPathP
ctypedef UP[ISymbolRefPath] ISymbolRefPathUP
ctypedef IActivityMatchChoice *IActivityMatchChoiceP
ctypedef UP[IActivityMatchChoice] IActivityMatchChoiceUP
ctypedef IAssocData *IAssocDataP
ctypedef UP[IAssocData] IAssocDataUP
ctypedef IMonitorActivityMatchChoice *IMonitorActivityMatchChoiceP
ctypedef UP[IMonitorActivityMatchChoice] IMonitorActivityMatchChoiceUP
ctypedef ITemplateParamDeclList *ITemplateParamDeclListP
ctypedef UP[ITemplateParamDeclList] ITemplateParamDeclListUP
ctypedef IActivitySelectBranch *IActivitySelectBranchP
ctypedef UP[IActivitySelectBranch] IActivitySelectBranchUP
ctypedef ITemplateParamValue *ITemplateParamValueP
ctypedef UP[ITemplateParamValue] ITemplateParamValueUP
ctypedef ITemplateParamValueList *ITemplateParamValueListP
ctypedef UP[ITemplateParamValueList] ITemplateParamValueListUP
ctypedef IExecTargetTemplateParam *IExecTargetTemplateParamP
ctypedef UP[IExecTargetTemplateParam] IExecTargetTemplateParamUP
ctypedef IExpr *IExprP
ctypedef UP[IExpr] IExprUP
ctypedef IMonitorActivityStmt *IMonitorActivityStmtP
ctypedef UP[IMonitorActivityStmt] IMonitorActivityStmtUP
ctypedef INamedScopeChild *INamedScopeChildP
ctypedef UP[INamedScopeChild] INamedScopeChildUP
ctypedef IActivityJoinSpecBranch *IActivityJoinSpecBranchP
ctypedef UP[IActivityJoinSpecBranch] IActivityJoinSpecBranchUP
ctypedef IActivityJoinSpecFirst *IActivityJoinSpecFirstP
ctypedef UP[IActivityJoinSpecFirst] IActivityJoinSpecFirstUP
ctypedef IActivityJoinSpecNone *IActivityJoinSpecNoneP
ctypedef UP[IActivityJoinSpecNone] IActivityJoinSpecNoneUP
ctypedef IActivityJoinSpecSelect *IActivityJoinSpecSelectP
ctypedef UP[IActivityJoinSpecSelect] IActivityJoinSpecSelectUP
ctypedef IPackageImportStmt *IPackageImportStmtP
ctypedef UP[IPackageImportStmt] IPackageImportStmtUP
ctypedef IProceduralStmtIfClause *IProceduralStmtIfClauseP
ctypedef UP[IProceduralStmtIfClause] IProceduralStmtIfClauseUP
ctypedef IActivitySchedulingConstraint *IActivitySchedulingConstraintP
ctypedef UP[IActivitySchedulingConstraint] IActivitySchedulingConstraintUP
ctypedef IActivityStmt *IActivityStmtP
ctypedef UP[IActivityStmt] IActivityStmtUP
ctypedef IPyImportFromStmt *IPyImportFromStmtP
ctypedef UP[IPyImportFromStmt] IPyImportFromStmtUP
ctypedef IPyImportStmt *IPyImportStmtP
ctypedef UP[IPyImportStmt] IPyImportStmtUP
ctypedef IConstraintStmt *IConstraintStmtP
ctypedef UP[IConstraintStmt] IConstraintStmtUP
ctypedef IRefExprScopeIndex *IRefExprScopeIndexP
ctypedef UP[IRefExprScopeIndex] IRefExprScopeIndexUP
ctypedef IRefExprTypeScopeContext *IRefExprTypeScopeContextP
ctypedef UP[IRefExprTypeScopeContext] IRefExprTypeScopeContextUP
ctypedef IRefExprTypeScopeGlobal *IRefExprTypeScopeGlobalP
ctypedef UP[IRefExprTypeScopeGlobal] IRefExprTypeScopeGlobalUP
ctypedef IScope *IScopeP
ctypedef UP[IScope] IScopeUP
ctypedef IScopeChildRef *IScopeChildRefP
ctypedef UP[IScopeChildRef] IScopeChildRefUP
ctypedef ISymbolChild *ISymbolChildP
ctypedef UP[ISymbolChild] ISymbolChildUP
ctypedef ICoverStmtInline *ICoverStmtInlineP
ctypedef UP[ICoverStmtInline] ICoverStmtInlineUP
ctypedef ICoverStmtReference *ICoverStmtReferenceP
ctypedef UP[ICoverStmtReference] ICoverStmtReferenceUP
ctypedef IDataType *IDataTypeP
ctypedef UP[IDataType] IDataTypeUP
ctypedef ISymbolScopeRef *ISymbolScopeRefP
ctypedef UP[ISymbolScopeRef] ISymbolScopeRefUP
ctypedef ITemplateParamDecl *ITemplateParamDeclP
ctypedef UP[ITemplateParamDecl] ITemplateParamDeclUP
ctypedef ITemplateParamExprValue *ITemplateParamExprValueP
ctypedef UP[ITemplateParamExprValue] ITemplateParamExprValueUP
ctypedef ITemplateParamTypeValue *ITemplateParamTypeValueP
ctypedef UP[ITemplateParamTypeValue] ITemplateParamTypeValueUP
ctypedef IExecStmt *IExecStmtP
ctypedef UP[IExecStmt] IExecStmtUP
ctypedef IExecTargetTemplateBlock *IExecTargetTemplateBlockP
ctypedef UP[IExecTargetTemplateBlock] IExecTargetTemplateBlockUP
ctypedef ITypeIdentifier *ITypeIdentifierP
ctypedef UP[ITypeIdentifier] ITypeIdentifierUP
ctypedef ITypeIdentifierElem *ITypeIdentifierElemP
ctypedef UP[ITypeIdentifierElem] ITypeIdentifierElemUP
ctypedef IExprAggrLiteral *IExprAggrLiteralP
ctypedef UP[IExprAggrLiteral] IExprAggrLiteralUP
ctypedef IExprBin *IExprBinP
ctypedef UP[IExprBin] IExprBinUP
ctypedef IExprBitSlice *IExprBitSliceP
ctypedef UP[IExprBitSlice] IExprBitSliceUP
ctypedef IExprBool *IExprBoolP
ctypedef UP[IExprBool] IExprBoolUP
ctypedef IExprCast *IExprCastP
ctypedef UP[IExprCast] IExprCastUP
ctypedef IExprCompileHas *IExprCompileHasP
ctypedef UP[IExprCompileHas] IExprCompileHasUP
ctypedef IExprCond *IExprCondP
ctypedef UP[IExprCond] IExprCondUP
ctypedef IExprDomainOpenRangeList *IExprDomainOpenRangeListP
ctypedef UP[IExprDomainOpenRangeList] IExprDomainOpenRangeListUP
ctypedef IExprDomainOpenRangeValue *IExprDomainOpenRangeValueP
ctypedef UP[IExprDomainOpenRangeValue] IExprDomainOpenRangeValueUP
ctypedef IExprHierarchicalId *IExprHierarchicalIdP
ctypedef UP[IExprHierarchicalId] IExprHierarchicalIdUP
ctypedef IExprId *IExprIdP
ctypedef UP[IExprId] IExprIdUP
ctypedef IExprIn *IExprInP
ctypedef UP[IExprIn] IExprInUP
ctypedef IExprListLiteral *IExprListLiteralP
ctypedef UP[IExprListLiteral] IExprListLiteralUP
ctypedef IExprMemberPathElem *IExprMemberPathElemP
ctypedef UP[IExprMemberPathElem] IExprMemberPathElemUP
ctypedef IExprNull *IExprNullP
ctypedef UP[IExprNull] IExprNullUP
ctypedef IExprNumber *IExprNumberP
ctypedef UP[IExprNumber] IExprNumberUP
ctypedef IExprOpenRangeList *IExprOpenRangeListP
ctypedef UP[IExprOpenRangeList] IExprOpenRangeListUP
ctypedef IExprOpenRangeValue *IExprOpenRangeValueP
ctypedef UP[IExprOpenRangeValue] IExprOpenRangeValueUP
ctypedef IExprRefPath *IExprRefPathP
ctypedef UP[IExprRefPath] IExprRefPathUP
ctypedef IExprRefPathElem *IExprRefPathElemP
ctypedef UP[IExprRefPathElem] IExprRefPathElemUP
ctypedef IExprStaticRefPath *IExprStaticRefPathP
ctypedef UP[IExprStaticRefPath] IExprStaticRefPathUP
ctypedef IExprString *IExprStringP
ctypedef UP[IExprString] IExprStringUP
ctypedef IExprStructLiteral *IExprStructLiteralP
ctypedef UP[IExprStructLiteral] IExprStructLiteralUP
ctypedef IExprStructLiteralItem *IExprStructLiteralItemP
ctypedef UP[IExprStructLiteralItem] IExprStructLiteralItemUP
ctypedef IExprSubscript *IExprSubscriptP
ctypedef UP[IExprSubscript] IExprSubscriptUP
ctypedef IExprSubstring *IExprSubstringP
ctypedef UP[IExprSubstring] IExprSubstringUP
ctypedef IExprUnary *IExprUnaryP
ctypedef UP[IExprUnary] IExprUnaryUP
ctypedef IExtendEnum *IExtendEnumP
ctypedef UP[IExtendEnum] IExtendEnumUP
ctypedef IFunctionDefinition *IFunctionDefinitionP
ctypedef UP[IFunctionDefinition] IFunctionDefinitionUP
ctypedef IFunctionImport *IFunctionImportP
ctypedef UP[IFunctionImport] IFunctionImportUP
ctypedef IFunctionParamDecl *IFunctionParamDeclP
ctypedef UP[IFunctionParamDecl] IFunctionParamDeclUP
ctypedef IMethodParameterList *IMethodParameterListP
ctypedef UP[IMethodParameterList] IMethodParameterListUP
ctypedef IMonitorActivityRepeatCount *IMonitorActivityRepeatCountP
ctypedef UP[IMonitorActivityRepeatCount] IMonitorActivityRepeatCountUP
ctypedef IMonitorActivityRepeatWhile *IMonitorActivityRepeatWhileP
ctypedef UP[IMonitorActivityRepeatWhile] IMonitorActivityRepeatWhileUP
ctypedef IMonitorActivitySelect *IMonitorActivitySelectP
ctypedef UP[IMonitorActivitySelect] IMonitorActivitySelectUP
ctypedef IActivityBindStmt *IActivityBindStmtP
ctypedef UP[IActivityBindStmt] IActivityBindStmtUP
ctypedef IActivityConstraint *IActivityConstraintP
ctypedef UP[IActivityConstraint] IActivityConstraintUP
ctypedef IMonitorConstraint *IMonitorConstraintP
ctypedef UP[IMonitorConstraint] IMonitorConstraintUP
ctypedef INamedScope *INamedScopeP
ctypedef UP[INamedScope] INamedScopeUP
ctypedef IPackageScope *IPackageScopeP
ctypedef UP[IPackageScope] IPackageScopeUP
ctypedef IProceduralStmtAssignment *IProceduralStmtAssignmentP
ctypedef UP[IProceduralStmtAssignment] IProceduralStmtAssignmentUP
ctypedef IProceduralStmtBody *IProceduralStmtBodyP
ctypedef UP[IProceduralStmtBody] IProceduralStmtBodyUP
ctypedef IProceduralStmtBreak *IProceduralStmtBreakP
ctypedef UP[IProceduralStmtBreak] IProceduralStmtBreakUP
ctypedef IActivityLabeledStmt *IActivityLabeledStmtP
ctypedef UP[IActivityLabeledStmt] IActivityLabeledStmtUP
ctypedef IProceduralStmtContinue *IProceduralStmtContinueP
ctypedef UP[IProceduralStmtContinue] IProceduralStmtContinueUP
ctypedef IProceduralStmtDataDeclaration *IProceduralStmtDataDeclarationP
ctypedef UP[IProceduralStmtDataDeclaration] IProceduralStmtDataDeclarationUP
ctypedef IProceduralStmtExpr *IProceduralStmtExprP
ctypedef UP[IProceduralStmtExpr] IProceduralStmtExprUP
ctypedef IProceduralStmtFunctionCall *IProceduralStmtFunctionCallP
ctypedef UP[IProceduralStmtFunctionCall] IProceduralStmtFunctionCallUP
ctypedef IProceduralStmtIfElse *IProceduralStmtIfElseP
ctypedef UP[IProceduralStmtIfElse] IProceduralStmtIfElseUP
ctypedef IProceduralStmtMatch *IProceduralStmtMatchP
ctypedef UP[IProceduralStmtMatch] IProceduralStmtMatchUP
ctypedef IProceduralStmtMatchChoice *IProceduralStmtMatchChoiceP
ctypedef UP[IProceduralStmtMatchChoice] IProceduralStmtMatchChoiceUP
ctypedef IProceduralStmtRandomize *IProceduralStmtRandomizeP
ctypedef UP[IProceduralStmtRandomize] IProceduralStmtRandomizeUP
ctypedef IProceduralStmtReturn *IProceduralStmtReturnP
ctypedef UP[IProceduralStmtReturn] IProceduralStmtReturnUP
ctypedef IProceduralStmtYield *IProceduralStmtYieldP
ctypedef UP[IProceduralStmtYield] IProceduralStmtYieldUP
ctypedef IConstraintScope *IConstraintScopeP
ctypedef UP[IConstraintScope] IConstraintScopeUP
ctypedef IConstraintStmtDefault *IConstraintStmtDefaultP
ctypedef UP[IConstraintStmtDefault] IConstraintStmtDefaultUP
ctypedef IConstraintStmtDefaultDisable *IConstraintStmtDefaultDisableP
ctypedef UP[IConstraintStmtDefaultDisable] IConstraintStmtDefaultDisableUP
ctypedef IConstraintStmtExpr *IConstraintStmtExprP
ctypedef UP[IConstraintStmtExpr] IConstraintStmtExprUP
ctypedef IConstraintStmtField *IConstraintStmtFieldP
ctypedef UP[IConstraintStmtField] IConstraintStmtFieldUP
ctypedef IConstraintStmtIf *IConstraintStmtIfP
ctypedef UP[IConstraintStmtIf] IConstraintStmtIfUP
ctypedef IConstraintStmtUnique *IConstraintStmtUniqueP
ctypedef UP[IConstraintStmtUnique] IConstraintStmtUniqueUP
ctypedef ISymbolChildrenScope *ISymbolChildrenScopeP
ctypedef UP[ISymbolChildrenScope] ISymbolChildrenScopeUP
ctypedef IDataTypeBool *IDataTypeBoolP
ctypedef UP[IDataTypeBool] IDataTypeBoolUP
ctypedef IDataTypeChandle *IDataTypeChandleP
ctypedef UP[IDataTypeChandle] IDataTypeChandleUP
ctypedef IDataTypeEnum *IDataTypeEnumP
ctypedef UP[IDataTypeEnum] IDataTypeEnumUP
ctypedef IDataTypeInt *IDataTypeIntP
ctypedef UP[IDataTypeInt] IDataTypeIntUP
ctypedef IDataTypePyObj *IDataTypePyObjP
ctypedef UP[IDataTypePyObj] IDataTypePyObjUP
ctypedef IDataTypeRef *IDataTypeRefP
ctypedef UP[IDataTypeRef] IDataTypeRefUP
ctypedef IDataTypeString *IDataTypeStringP
ctypedef UP[IDataTypeString] IDataTypeStringUP
ctypedef IDataTypeUserDefined *IDataTypeUserDefinedP
ctypedef UP[IDataTypeUserDefined] IDataTypeUserDefinedUP
ctypedef IEnumDecl *IEnumDeclP
ctypedef UP[IEnumDecl] IEnumDeclUP
ctypedef IEnumItem *IEnumItemP
ctypedef UP[IEnumItem] IEnumItemUP
ctypedef ITemplateCategoryTypeParamDecl *ITemplateCategoryTypeParamDeclP
ctypedef UP[ITemplateCategoryTypeParamDecl] ITemplateCategoryTypeParamDeclUP
ctypedef ITemplateGenericTypeParamDecl *ITemplateGenericTypeParamDeclP
ctypedef UP[ITemplateGenericTypeParamDecl] ITemplateGenericTypeParamDeclUP
ctypedef ITemplateValueParamDecl *ITemplateValueParamDeclP
ctypedef UP[ITemplateValueParamDecl] ITemplateValueParamDeclUP
ctypedef IExprAggrEmpty *IExprAggrEmptyP
ctypedef UP[IExprAggrEmpty] IExprAggrEmptyUP
ctypedef IExprAggrList *IExprAggrListP
ctypedef UP[IExprAggrList] IExprAggrListUP
ctypedef IExprAggrMap *IExprAggrMapP
ctypedef UP[IExprAggrMap] IExprAggrMapUP
ctypedef IExprAggrStruct *IExprAggrStructP
ctypedef UP[IExprAggrStruct] IExprAggrStructUP
ctypedef IExprRefPathContext *IExprRefPathContextP
ctypedef UP[IExprRefPathContext] IExprRefPathContextUP
ctypedef IExprRefPathId *IExprRefPathIdP
ctypedef UP[IExprRefPathId] IExprRefPathIdUP
ctypedef IExprRefPathStatic *IExprRefPathStaticP
ctypedef UP[IExprRefPathStatic] IExprRefPathStaticUP
ctypedef IExprRefPathStaticRooted *IExprRefPathStaticRootedP
ctypedef UP[IExprRefPathStaticRooted] IExprRefPathStaticRootedUP
ctypedef IExprSignedNumber *IExprSignedNumberP
ctypedef UP[IExprSignedNumber] IExprSignedNumberUP
ctypedef IExprUnsignedNumber *IExprUnsignedNumberP
ctypedef UP[IExprUnsignedNumber] IExprUnsignedNumberUP
ctypedef IExtendType *IExtendTypeP
ctypedef UP[IExtendType] IExtendTypeUP
ctypedef IField *IFieldP
ctypedef UP[IField] IFieldUP
ctypedef IFieldClaim *IFieldClaimP
ctypedef UP[IFieldClaim] IFieldClaimUP
ctypedef IFieldCompRef *IFieldCompRefP
ctypedef UP[IFieldCompRef] IFieldCompRefUP
ctypedef IFieldRef *IFieldRefP
ctypedef UP[IFieldRef] IFieldRefUP
ctypedef IFunctionImportProto *IFunctionImportProtoP
ctypedef UP[IFunctionImportProto] IFunctionImportProtoUP
ctypedef IFunctionImportType *IFunctionImportTypeP
ctypedef UP[IFunctionImportType] IFunctionImportTypeUP
ctypedef IFunctionPrototype *IFunctionPrototypeP
ctypedef UP[IFunctionPrototype] IFunctionPrototypeUP
ctypedef IGlobalScope *IGlobalScopeP
ctypedef UP[IGlobalScope] IGlobalScopeUP
ctypedef IMonitorActivityActionTraversal *IMonitorActivityActionTraversalP
ctypedef UP[IMonitorActivityActionTraversal] IMonitorActivityActionTraversalUP
ctypedef IMonitorActivityConcat *IMonitorActivityConcatP
ctypedef UP[IMonitorActivityConcat] IMonitorActivityConcatUP
ctypedef IMonitorActivityEventually *IMonitorActivityEventuallyP
ctypedef UP[IMonitorActivityEventually] IMonitorActivityEventuallyUP
ctypedef IMonitorActivityIfElse *IMonitorActivityIfElseP
ctypedef UP[IMonitorActivityIfElse] IMonitorActivityIfElseUP
ctypedef IMonitorActivityMatch *IMonitorActivityMatchP
ctypedef UP[IMonitorActivityMatch] IMonitorActivityMatchUP
ctypedef IMonitorActivityMonitorTraversal *IMonitorActivityMonitorTraversalP
ctypedef UP[IMonitorActivityMonitorTraversal] IMonitorActivityMonitorTraversalUP
ctypedef IMonitorActivityOverlap *IMonitorActivityOverlapP
ctypedef UP[IMonitorActivityOverlap] IMonitorActivityOverlapUP
ctypedef IActivityActionHandleTraversal *IActivityActionHandleTraversalP
ctypedef UP[IActivityActionHandleTraversal] IActivityActionHandleTraversalUP
ctypedef IActivityActionTypeTraversal *IActivityActionTypeTraversalP
ctypedef UP[IActivityActionTypeTraversal] IActivityActionTypeTraversalUP
ctypedef IActivityAtomicBlock *IActivityAtomicBlockP
ctypedef UP[IActivityAtomicBlock] IActivityAtomicBlockUP
ctypedef IActivityForeach *IActivityForeachP
ctypedef UP[IActivityForeach] IActivityForeachUP
ctypedef IActivityIfElse *IActivityIfElseP
ctypedef UP[IActivityIfElse] IActivityIfElseUP
ctypedef IActivityMatch *IActivityMatchP
ctypedef UP[IActivityMatch] IActivityMatchUP
ctypedef IActivityRepeatCount *IActivityRepeatCountP
ctypedef UP[IActivityRepeatCount] IActivityRepeatCountUP
ctypedef IActivityRepeatWhile *IActivityRepeatWhileP
ctypedef UP[IActivityRepeatWhile] IActivityRepeatWhileUP
ctypedef IActivityReplicate *IActivityReplicateP
ctypedef UP[IActivityReplicate] IActivityReplicateUP
ctypedef IActivitySelect *IActivitySelectP
ctypedef UP[IActivitySelect] IActivitySelectUP
ctypedef IProceduralStmtRepeatWhile *IProceduralStmtRepeatWhileP
ctypedef UP[IProceduralStmtRepeatWhile] IProceduralStmtRepeatWhileUP
ctypedef IActivitySuper *IActivitySuperP
ctypedef UP[IActivitySuper] IActivitySuperUP
ctypedef IProceduralStmtWhile *IProceduralStmtWhileP
ctypedef UP[IProceduralStmtWhile] IProceduralStmtWhileUP
ctypedef IConstraintBlock *IConstraintBlockP
ctypedef UP[IConstraintBlock] IConstraintBlockUP
ctypedef IConstraintStmtForall *IConstraintStmtForallP
ctypedef UP[IConstraintStmtForall] IConstraintStmtForallUP
ctypedef IConstraintStmtForeach *IConstraintStmtForeachP
ctypedef UP[IConstraintStmtForeach] IConstraintStmtForeachUP
ctypedef IConstraintStmtImplication *IConstraintStmtImplicationP
ctypedef UP[IConstraintStmtImplication] IConstraintStmtImplicationUP
ctypedef ISymbolScope *ISymbolScopeP
ctypedef UP[ISymbolScope] ISymbolScopeUP
ctypedef ITypeScope *ITypeScopeP
ctypedef UP[ITypeScope] ITypeScopeUP
ctypedef IExprRefPathStaticFunc *IExprRefPathStaticFuncP
ctypedef UP[IExprRefPathStaticFunc] IExprRefPathStaticFuncUP
ctypedef IExprRefPathSuper *IExprRefPathSuperP
ctypedef UP[IExprRefPathSuper] IExprRefPathSuperUP
ctypedef IAction *IActionP
ctypedef UP[IAction] IActionUP
ctypedef IMonitorActivitySchedule *IMonitorActivityScheduleP
ctypedef UP[IMonitorActivitySchedule] IMonitorActivityScheduleUP
ctypedef IMonitorActivitySequence *IMonitorActivitySequenceP
ctypedef UP[IMonitorActivitySequence] IMonitorActivitySequenceUP
ctypedef IActivityDecl *IActivityDeclP
ctypedef UP[IActivityDecl] IActivityDeclUP
ctypedef IRootSymbolScope *IRootSymbolScopeP
ctypedef UP[IRootSymbolScope] IRootSymbolScopeUP
ctypedef IStruct *IStructP
ctypedef UP[IStruct] IStructUP
ctypedef IConstraintSymbolScope *IConstraintSymbolScopeP
ctypedef UP[IConstraintSymbolScope] IConstraintSymbolScopeUP
ctypedef ISymbolEnumScope *ISymbolEnumScopeP
ctypedef UP[ISymbolEnumScope] ISymbolEnumScopeUP
ctypedef ISymbolExtendScope *ISymbolExtendScopeP
ctypedef UP[ISymbolExtendScope] ISymbolExtendScopeUP
ctypedef IActivityLabeledScope *IActivityLabeledScopeP
ctypedef UP[IActivityLabeledScope] IActivityLabeledScopeUP
ctypedef ISymbolFunctionScope *ISymbolFunctionScopeP
ctypedef UP[ISymbolFunctionScope] ISymbolFunctionScopeUP
ctypedef ISymbolTypeScope *ISymbolTypeScopeP
ctypedef UP[ISymbolTypeScope] ISymbolTypeScopeUP
ctypedef IMonitor *IMonitorP
ctypedef UP[IMonitor] IMonitorUP
ctypedef IMonitorActivityDecl *IMonitorActivityDeclP
ctypedef UP[IMonitorActivityDecl] IMonitorActivityDeclUP
ctypedef IExecScope *IExecScopeP
ctypedef UP[IExecScope] IExecScopeUP
ctypedef IProceduralStmtSymbolBodyScope *IProceduralStmtSymbolBodyScopeP
ctypedef UP[IProceduralStmtSymbolBodyScope] IProceduralStmtSymbolBodyScopeUP
ctypedef IComponent *IComponentP
ctypedef UP[IComponent] IComponentUP
ctypedef IProceduralStmtRepeat *IProceduralStmtRepeatP
ctypedef UP[IProceduralStmtRepeat] IProceduralStmtRepeatUP
ctypedef IActivityParallel *IActivityParallelP
ctypedef UP[IActivityParallel] IActivityParallelUP
ctypedef IProceduralStmtForeach *IProceduralStmtForeachP
ctypedef UP[IProceduralStmtForeach] IProceduralStmtForeachUP
ctypedef IActivitySchedule *IActivityScheduleP
ctypedef UP[IActivitySchedule] IActivityScheduleUP
ctypedef IExecBlock *IExecBlockP
ctypedef UP[IExecBlock] IExecBlockUP
ctypedef IActivitySequence *IActivitySequenceP
ctypedef UP[IActivitySequence] IActivitySequenceUP
cdef extern from "zsp/ast/AssignOp.h" namespace "zsp::ast":
    cdef enum AssignOp:
        AssignOp_AssignOp_Eq "zsp::ast::AssignOp::AssignOp_Eq"
        AssignOp_AssignOp_PlusEq "zsp::ast::AssignOp::AssignOp_PlusEq"
        AssignOp_AssignOp_MinusEq "zsp::ast::AssignOp::AssignOp_MinusEq"
        AssignOp_AssignOp_ShlEq "zsp::ast::AssignOp::AssignOp_ShlEq"
        AssignOp_AssignOp_ShrEq "zsp::ast::AssignOp::AssignOp_ShrEq"
        AssignOp_AssignOp_OrEq "zsp::ast::AssignOp::AssignOp_OrEq"
        AssignOp_AssignOp_AndEq "zsp::ast::AssignOp::AssignOp_AndEq"
cdef extern from "zsp/ast/ExecKind.h" namespace "zsp::ast":
    cdef enum ExecKind:
        ExecKind_ExecKind_Body "zsp::ast::ExecKind::ExecKind_Body"
        ExecKind_ExecKind_Header "zsp::ast::ExecKind::ExecKind_Header"
        ExecKind_ExecKind_Declaration "zsp::ast::ExecKind::ExecKind_Declaration"
        ExecKind_ExecKind_RunStart "zsp::ast::ExecKind::ExecKind_RunStart"
        ExecKind_ExecKind_RunEnd "zsp::ast::ExecKind::ExecKind_RunEnd"
        ExecKind_ExecKind_InitDown "zsp::ast::ExecKind::ExecKind_InitDown"
        ExecKind_ExecKind_InitUp "zsp::ast::ExecKind::ExecKind_InitUp"
        ExecKind_ExecKind_PreSolve "zsp::ast::ExecKind::ExecKind_PreSolve"
        ExecKind_ExecKind_PostSolve "zsp::ast::ExecKind::ExecKind_PostSolve"
cdef extern from "zsp/ast/ExprBinOp.h" namespace "zsp::ast":
    cdef enum ExprBinOp:
        ExprBinOp_BinOp_LogOr "zsp::ast::ExprBinOp::BinOp_LogOr"
        ExprBinOp_BinOp_LogAnd "zsp::ast::ExprBinOp::BinOp_LogAnd"
        ExprBinOp_BinOp_BitOr "zsp::ast::ExprBinOp::BinOp_BitOr"
        ExprBinOp_BinOp_BitXor "zsp::ast::ExprBinOp::BinOp_BitXor"
        ExprBinOp_BinOp_BitAnd "zsp::ast::ExprBinOp::BinOp_BitAnd"
        ExprBinOp_BinOp_Lt "zsp::ast::ExprBinOp::BinOp_Lt"
        ExprBinOp_BinOp_Le "zsp::ast::ExprBinOp::BinOp_Le"
        ExprBinOp_BinOp_Gt "zsp::ast::ExprBinOp::BinOp_Gt"
        ExprBinOp_BinOp_Ge "zsp::ast::ExprBinOp::BinOp_Ge"
        ExprBinOp_BinOp_Exp "zsp::ast::ExprBinOp::BinOp_Exp"
        ExprBinOp_BinOp_Mul "zsp::ast::ExprBinOp::BinOp_Mul"
        ExprBinOp_BinOp_Div "zsp::ast::ExprBinOp::BinOp_Div"
        ExprBinOp_BinOp_Mod "zsp::ast::ExprBinOp::BinOp_Mod"
        ExprBinOp_BinOp_Add "zsp::ast::ExprBinOp::BinOp_Add"
        ExprBinOp_BinOp_Sub "zsp::ast::ExprBinOp::BinOp_Sub"
        ExprBinOp_BinOp_Shl "zsp::ast::ExprBinOp::BinOp_Shl"
        ExprBinOp_BinOp_Shr "zsp::ast::ExprBinOp::BinOp_Shr"
        ExprBinOp_BinOp_Eq "zsp::ast::ExprBinOp::BinOp_Eq"
        ExprBinOp_BinOp_Ne "zsp::ast::ExprBinOp::BinOp_Ne"
cdef extern from "zsp/ast/ExprUnaryOp.h" namespace "zsp::ast":
    cdef enum ExprUnaryOp:
        ExprUnaryOp_UnaryOp_Plus "zsp::ast::ExprUnaryOp::UnaryOp_Plus"
        ExprUnaryOp_UnaryOp_Minus "zsp::ast::ExprUnaryOp::UnaryOp_Minus"
        ExprUnaryOp_UnaryOp_LogNot "zsp::ast::ExprUnaryOp::UnaryOp_LogNot"
        ExprUnaryOp_UnaryOp_BitNeg "zsp::ast::ExprUnaryOp::UnaryOp_BitNeg"
        ExprUnaryOp_UnaryOp_BitAnd "zsp::ast::ExprUnaryOp::UnaryOp_BitAnd"
        ExprUnaryOp_UnaryOp_BitOr "zsp::ast::ExprUnaryOp::UnaryOp_BitOr"
        ExprUnaryOp_UnaryOp_BitXor "zsp::ast::ExprUnaryOp::UnaryOp_BitXor"
cdef extern from "zsp/ast/ExtendTargetE.h" namespace "zsp::ast":
    cdef enum ExtendTargetE:
        ExtendTargetE_Action "zsp::ast::ExtendTargetE::Action"
        ExtendTargetE_Buffer "zsp::ast::ExtendTargetE::Buffer"
        ExtendTargetE_Component "zsp::ast::ExtendTargetE::Component"
        ExtendTargetE_Enum "zsp::ast::ExtendTargetE::Enum"
        ExtendTargetE_Resource "zsp::ast::ExtendTargetE::Resource"
        ExtendTargetE_State "zsp::ast::ExtendTargetE::State"
        ExtendTargetE_Stream "zsp::ast::ExtendTargetE::Stream"
        ExtendTargetE_Struct "zsp::ast::ExtendTargetE::Struct"
cdef extern from "zsp/ast/FunctionParamDeclKind.h" namespace "zsp::ast":
    cdef enum FunctionParamDeclKind:
        FunctionParamDeclKind_ParamKind_DataType "zsp::ast::FunctionParamDeclKind::ParamKind_DataType"
        FunctionParamDeclKind_ParamKind_Type "zsp::ast::FunctionParamDeclKind::ParamKind_Type"
        FunctionParamDeclKind_ParamKind_RefAction "zsp::ast::FunctionParamDeclKind::ParamKind_RefAction"
        FunctionParamDeclKind_ParamKind_RefComponent "zsp::ast::FunctionParamDeclKind::ParamKind_RefComponent"
        FunctionParamDeclKind_ParamKind_RefBuffer "zsp::ast::FunctionParamDeclKind::ParamKind_RefBuffer"
        FunctionParamDeclKind_ParamKind_RefResource "zsp::ast::FunctionParamDeclKind::ParamKind_RefResource"
        FunctionParamDeclKind_ParamKind_RefState "zsp::ast::FunctionParamDeclKind::ParamKind_RefState"
        FunctionParamDeclKind_ParamKind_RefStream "zsp::ast::FunctionParamDeclKind::ParamKind_RefStream"
        FunctionParamDeclKind_ParamKind_RefStruct "zsp::ast::FunctionParamDeclKind::ParamKind_RefStruct"
        FunctionParamDeclKind_ParamKind_Struct "zsp::ast::FunctionParamDeclKind::ParamKind_Struct"
cdef extern from "zsp/ast/ParamDir.h" namespace "zsp::ast":
    cdef enum ParamDir:
        ParamDir_ParamDir_Default "zsp::ast::ParamDir::ParamDir_Default"
        ParamDir_ParamDir_In "zsp::ast::ParamDir::ParamDir_In"
        ParamDir_ParamDir_Out "zsp::ast::ParamDir::ParamDir_Out"
        ParamDir_ParamDir_InOut "zsp::ast::ParamDir::ParamDir_InOut"
cdef extern from "zsp/ast/PlatQual.h" namespace "zsp::ast":
    cdef enum PlatQual:
        PlatQual_PlatQual_None "zsp::ast::PlatQual::PlatQual_None"
        PlatQual_PlatQual_Target "zsp::ast::PlatQual::PlatQual_Target"
        PlatQual_PlatQual_Solve "zsp::ast::PlatQual::PlatQual_Solve"
cdef extern from "zsp/ast/StringMethodId.h" namespace "zsp::ast":
    cdef enum StringMethodId:
        StringMethodId_StringMethod_None "zsp::ast::StringMethodId::StringMethod_None"
        StringMethodId_StringMethod_Size "zsp::ast::StringMethodId::StringMethod_Size"
        StringMethodId_StringMethod_Find "zsp::ast::StringMethodId::StringMethod_Find"
        StringMethodId_StringMethod_FindLast "zsp::ast::StringMethodId::StringMethod_FindLast"
        StringMethodId_StringMethod_FindAll "zsp::ast::StringMethodId::StringMethod_FindAll"
        StringMethodId_StringMethod_Lower "zsp::ast::StringMethodId::StringMethod_Lower"
        StringMethodId_StringMethod_Upper "zsp::ast::StringMethodId::StringMethod_Upper"
        StringMethodId_StringMethod_Split "zsp::ast::StringMethodId::StringMethod_Split"
        StringMethodId_StringMethod_Chars "zsp::ast::StringMethodId::StringMethod_Chars"
cdef extern from "zsp/ast/StructKind.h" namespace "zsp::ast":
    cdef enum StructKind:
        StructKind_Buffer "zsp::ast::StructKind::Buffer"
        StructKind_Struct "zsp::ast::StructKind::Struct"
        StructKind_Resource "zsp::ast::StructKind::Resource"
        StructKind_Stream "zsp::ast::StructKind::Stream"
        StructKind_State "zsp::ast::StructKind::State"
cdef extern from "zsp/ast/SymbolRefPathElemKind.h" namespace "zsp::ast":
    cdef enum SymbolRefPathElemKind:
        SymbolRefPathElemKind_ElemKind_ChildIdx "zsp::ast::SymbolRefPathElemKind::ElemKind_ChildIdx"
        SymbolRefPathElemKind_ElemKind_ArgIdx "zsp::ast::SymbolRefPathElemKind::ElemKind_ArgIdx"
        SymbolRefPathElemKind_ElemKind_Inline "zsp::ast::SymbolRefPathElemKind::ElemKind_Inline"
        SymbolRefPathElemKind_ElemKind_ParamIdx "zsp::ast::SymbolRefPathElemKind::ElemKind_ParamIdx"
        SymbolRefPathElemKind_ElemKind_Super "zsp::ast::SymbolRefPathElemKind::ElemKind_Super"
        SymbolRefPathElemKind_ElemKind_TypeSpec "zsp::ast::SymbolRefPathElemKind::ElemKind_TypeSpec"
cdef extern from "zsp/ast/TypeCategory.h" namespace "zsp::ast":
    cdef enum TypeCategory:
        TypeCategory_Action "zsp::ast::TypeCategory::Action"
        TypeCategory_Component "zsp::ast::TypeCategory::Component"
        TypeCategory_Buffer "zsp::ast::TypeCategory::Buffer"
        TypeCategory_Resource "zsp::ast::TypeCategory::Resource"
        TypeCategory_State "zsp::ast::TypeCategory::State"
        TypeCategory_Stream "zsp::ast::TypeCategory::Stream"
        TypeCategory_Struct "zsp::ast::TypeCategory::Struct"
cdef extern from "zsp/ast/Location.h" namespace "zsp::ast":
    cdef cppclass Location:
        int32_t fileid
        int32_t lineno
        int32_t linepos
        int32_t extent
cdef extern from "zsp/ast/SymbolRefPathElem.h" namespace "zsp::ast":
    cdef cppclass SymbolRefPathElem:
        SymbolRefPathElemKind kind
        int32_t idx
cdef extern from "zsp/ast/FieldAttr.h" namespace "zsp::ast":
    cdef enum FieldAttr:
        FieldAttr_Action "zsp::ast::FieldAttr::Action"
        FieldAttr_Builtin "zsp::ast::FieldAttr::Builtin"
        FieldAttr_Rand "zsp::ast::FieldAttr::Rand"
        FieldAttr_Const "zsp::ast::FieldAttr::Const"
        FieldAttr_Static "zsp::ast::FieldAttr::Static"
        FieldAttr_Private "zsp::ast::FieldAttr::Private"
        FieldAttr_Protected "zsp::ast::FieldAttr::Protected"
ctypedef IFactory *IFactoryP
cdef extern from "zsp/ast/IFactory.h" namespace "zsp::ast":
    cdef cppclass IFactory:
        IRefExpr *mkRefExpr(
                )
        IExprAggrMapElem *mkExprAggrMapElem(
                IExprP lhs,
                IExprP rhs)
        IMonitorActivitySelectBranch *mkMonitorActivitySelectBranch(
                IExprP guard,
                IScopeChildP body)
        IExprAggrStructElem *mkExprAggrStructElem(
                IExprIdP name,
                IExprP value)
        IScopeChild *mkScopeChild(
                )
        IActivityJoinSpec *mkActivityJoinSpec(
                )
        ISymbolImportSpec *mkSymbolImportSpec(
                )
        ISymbolRefPath *mkSymbolRefPath(
                )
        IActivityMatchChoice *mkActivityMatchChoice(
                bool is_default,
                IExprOpenRangeListP cond,
                IScopeChildP body)
        IAssocData *mkAssocData(
                )
        IMonitorActivityMatchChoice *mkMonitorActivityMatchChoice(
                bool is_default,
                IExprOpenRangeListP cond,
                IScopeChildP body)
        ITemplateParamDeclList *mkTemplateParamDeclList(
                )
        IActivitySelectBranch *mkActivitySelectBranch(
                IExprP guard,
                IExprP weight,
                IScopeChildP body)
        ITemplateParamValue *mkTemplateParamValue(
                )
        ITemplateParamValueList *mkTemplateParamValueList(
                )
        IExecTargetTemplateParam *mkExecTargetTemplateParam(
                IExprP expr,
                int32_t start,
                int32_t end)
        IExpr *mkExpr(
                )
        IMonitorActivityStmt *mkMonitorActivityStmt(
                )
        INamedScopeChild *mkNamedScopeChild(
                IExprIdP name)
        IActivityJoinSpecBranch *mkActivityJoinSpecBranch(
                )
        IActivityJoinSpecFirst *mkActivityJoinSpecFirst(
                IExprP count)
        IActivityJoinSpecNone *mkActivityJoinSpecNone(
                )
        IActivityJoinSpecSelect *mkActivityJoinSpecSelect(
                IExprP count)
        IPackageImportStmt *mkPackageImportStmt(
                bool wildcard,
                IExprIdP alias)
        IProceduralStmtIfClause *mkProceduralStmtIfClause(
                IExprP cond,
                IScopeChildP body)
        IActivitySchedulingConstraint *mkActivitySchedulingConstraint(
                bool is_parallel)
        IActivityStmt *mkActivityStmt(
                )
        IPyImportFromStmt *mkPyImportFromStmt(
                )
        IPyImportStmt *mkPyImportStmt(
                )
        IConstraintStmt *mkConstraintStmt(
                )
        IRefExprScopeIndex *mkRefExprScopeIndex(
                IRefExprP base,
                int32_t offset)
        IRefExprTypeScopeContext *mkRefExprTypeScopeContext(
                IRefExprP base,
                int32_t offset)
        IRefExprTypeScopeGlobal *mkRefExprTypeScopeGlobal(
                int32_t fileid)
        IScope *mkScope(
                )
        IScopeChildRef *mkScopeChildRef(
                IScopeChildP target)
        ISymbolChild *mkSymbolChild(
                )
        ICoverStmtInline *mkCoverStmtInline(
                IScopeChildP body)
        ICoverStmtReference *mkCoverStmtReference(
                IExprRefPathP target)
        IDataType *mkDataType(
                )
        ISymbolScopeRef *mkSymbolScopeRef(
                std_string name)
        ITemplateParamDecl *mkTemplateParamDecl(
                IExprIdP name)
        ITemplateParamExprValue *mkTemplateParamExprValue(
                IExprP value)
        ITemplateParamTypeValue *mkTemplateParamTypeValue(
                IDataTypeP value)
        IExecStmt *mkExecStmt(
                )
        IExecTargetTemplateBlock *mkExecTargetTemplateBlock(
                ExecKind kind,
                std_string data)
        ITypeIdentifier *mkTypeIdentifier(
                )
        ITypeIdentifierElem *mkTypeIdentifierElem(
                IExprIdP id,
                ITemplateParamValueListP params)
        IExprAggrLiteral *mkExprAggrLiteral(
                )
        IExprBin *mkExprBin(
                IExprP lhs,
                ExprBinOp op,
                IExprP rhs)
        IExprBitSlice *mkExprBitSlice(
                IExprP lhs,
                IExprP rhs)
        IExprBool *mkExprBool(
                bool value)
        IExprCast *mkExprCast(
                IDataTypeP casting_type,
                IExprP expr)
        IExprCompileHas *mkExprCompileHas(
                IExprRefPathStaticP ref)
        IExprCond *mkExprCond(
                IExprP cond_e,
                IExprP true_e,
                IExprP false_e)
        IExprDomainOpenRangeList *mkExprDomainOpenRangeList(
                )
        IExprDomainOpenRangeValue *mkExprDomainOpenRangeValue(
                bool single,
                IExprP lhs,
                IExprP rhs)
        IExprHierarchicalId *mkExprHierarchicalId(
                )
        IExprId *mkExprId(
                std_string id,
                bool is_escaped)
        IExprIn *mkExprIn(
                IExprP lhs,
                IExprOpenRangeListP rhs)
        IExprListLiteral *mkExprListLiteral(
                )
        IExprMemberPathElem *mkExprMemberPathElem(
                IExprIdP id,
                IMethodParameterListP params)
        IExprNull *mkExprNull(
                )
        IExprNumber *mkExprNumber(
                )
        IExprOpenRangeList *mkExprOpenRangeList(
                )
        IExprOpenRangeValue *mkExprOpenRangeValue(
                IExprP lhs,
                IExprP rhs)
        IExprRefPath *mkExprRefPath(
                )
        IExprRefPathElem *mkExprRefPathElem(
                )
        IExprStaticRefPath *mkExprStaticRefPath(
                bool is_global,
                IExprMemberPathElemP leaf)
        IExprString *mkExprString(
                std_string value,
                bool is_raw)
        IExprStructLiteral *mkExprStructLiteral(
                )
        IExprStructLiteralItem *mkExprStructLiteralItem(
                IExprIdP id,
                IExprP value)
        IExprSubscript *mkExprSubscript(
                IExprP expr,
                IExprP subscript)
        IExprSubstring *mkExprSubstring(
                IExprP expr,
                IExprP start,
                IExprP end)
        IExprUnary *mkExprUnary(
                ExprUnaryOp op,
                IExprP rhs)
        IExtendEnum *mkExtendEnum(
                ITypeIdentifierP target)
        IFunctionDefinition *mkFunctionDefinition(
                IFunctionPrototypeP proto,
                IExecScopeP body,
                PlatQual plat)
        IFunctionImport *mkFunctionImport(
                PlatQual plat,
                std_string lang)
        IFunctionParamDecl *mkFunctionParamDecl(
                FunctionParamDeclKind kind,
                IExprIdP name,
                IDataTypeP type,
                ParamDir dir,
                IExprP dflt)
        IMethodParameterList *mkMethodParameterList(
                )
        IMonitorActivityRepeatCount *mkMonitorActivityRepeatCount(
                IExprIdP loop_var,
                IExprP count,
                IScopeChildP body)
        IMonitorActivityRepeatWhile *mkMonitorActivityRepeatWhile(
                IExprP cond,
                IScopeChildP body)
        IMonitorActivitySelect *mkMonitorActivitySelect(
                )
        IActivityBindStmt *mkActivityBindStmt(
                IExprHierarchicalIdP lhs)
        IActivityConstraint *mkActivityConstraint(
                IConstraintStmtP constraint)
        IMonitorConstraint *mkMonitorConstraint(
                IConstraintStmtP constraint)
        INamedScope *mkNamedScope(
                IExprIdP name)
        IPackageScope *mkPackageScope(
                )
        IProceduralStmtAssignment *mkProceduralStmtAssignment(
                IExprP lhs,
                AssignOp op,
                IExprP rhs)
        IProceduralStmtBody *mkProceduralStmtBody(
                IScopeChildP body)
        IProceduralStmtBreak *mkProceduralStmtBreak(
                )
        IActivityLabeledStmt *mkActivityLabeledStmt(
                )
        IProceduralStmtContinue *mkProceduralStmtContinue(
                )
        IProceduralStmtDataDeclaration *mkProceduralStmtDataDeclaration(
                IExprIdP name,
                IDataTypeP datatype,
                IExprP init)
        IProceduralStmtExpr *mkProceduralStmtExpr(
                IExprP expr)
        IProceduralStmtFunctionCall *mkProceduralStmtFunctionCall(
                IExprRefPathStaticRootedP prefix)
        IProceduralStmtIfElse *mkProceduralStmtIfElse(
                )
        IProceduralStmtMatch *mkProceduralStmtMatch(
                IExprP expr)
        IProceduralStmtMatchChoice *mkProceduralStmtMatchChoice(
                bool is_default,
                IExprOpenRangeListP cond,
                IScopeChildP body)
        IProceduralStmtRandomize *mkProceduralStmtRandomize(
                IExprP target)
        IProceduralStmtReturn *mkProceduralStmtReturn(
                IExprP expr)
        IProceduralStmtYield *mkProceduralStmtYield(
                )
        IConstraintScope *mkConstraintScope(
                )
        IConstraintStmtDefault *mkConstraintStmtDefault(
                IExprHierarchicalIdP hid,
                IExprP expr)
        IConstraintStmtDefaultDisable *mkConstraintStmtDefaultDisable(
                IExprHierarchicalIdP hid)
        IConstraintStmtExpr *mkConstraintStmtExpr(
                IExprP expr)
        IConstraintStmtField *mkConstraintStmtField(
                IExprIdP name,
                IDataTypeP type)
        IConstraintStmtIf *mkConstraintStmtIf(
                IExprP cond,
                IConstraintScopeP true_c,
                IConstraintScopeP false_c)
        IConstraintStmtUnique *mkConstraintStmtUnique(
                )
        ISymbolChildrenScope *mkSymbolChildrenScope(
                std_string name)
        IDataTypeBool *mkDataTypeBool(
                )
        IDataTypeChandle *mkDataTypeChandle(
                )
        IDataTypeEnum *mkDataTypeEnum(
                IDataTypeUserDefinedP tid,
                IExprOpenRangeListP in_rangelist)
        IDataTypeInt *mkDataTypeInt(
                bool is_signed,
                IExprP width,
                IExprDomainOpenRangeListP in_range)
        IDataTypePyObj *mkDataTypePyObj(
                )
        IDataTypeRef *mkDataTypeRef(
                IDataTypeUserDefinedP type)
        IDataTypeString *mkDataTypeString(
                bool has_range)
        IDataTypeUserDefined *mkDataTypeUserDefined(
                bool is_global,
                ITypeIdentifierP type_id)
        IEnumDecl *mkEnumDecl(
                IExprIdP name)
        IEnumItem *mkEnumItem(
                IExprIdP name,
                IExprP value)
        ITemplateCategoryTypeParamDecl *mkTemplateCategoryTypeParamDecl(
                IExprIdP name,
                TypeCategory category,
                ITypeIdentifierP restriction,
                IDataTypeP dflt)
        ITemplateGenericTypeParamDecl *mkTemplateGenericTypeParamDecl(
                IExprIdP name,
                IDataTypeP dflt)
        ITemplateValueParamDecl *mkTemplateValueParamDecl(
                IExprIdP name,
                IDataTypeP type,
                IExprP dflt)
        IExprAggrEmpty *mkExprAggrEmpty(
                )
        IExprAggrList *mkExprAggrList(
                )
        IExprAggrMap *mkExprAggrMap(
                )
        IExprAggrStruct *mkExprAggrStruct(
                )
        IExprRefPathContext *mkExprRefPathContext(
                IExprHierarchicalIdP hier_id)
        IExprRefPathId *mkExprRefPathId(
                IExprIdP id)
        IExprRefPathStatic *mkExprRefPathStatic(
                bool is_global)
        IExprRefPathStaticRooted *mkExprRefPathStaticRooted(
                IExprRefPathStaticP root,
                IExprHierarchicalIdP leaf)
        IExprSignedNumber *mkExprSignedNumber(
                std_string image,
                int32_t width,
                int64_t value)
        IExprUnsignedNumber *mkExprUnsignedNumber(
                std_string image,
                int32_t width,
                uint64_t value)
        IExtendType *mkExtendType(
                ExtendTargetE kind,
                ITypeIdentifierP target)
        IField *mkField(
                IExprIdP name,
                IDataTypeP type,
                FieldAttr attr,
                IExprP init)
        IFieldClaim *mkFieldClaim(
                IExprIdP name,
                IDataTypeUserDefinedP type,
                bool is_lock)
        IFieldCompRef *mkFieldCompRef(
                IExprIdP name,
                IDataTypeUserDefinedP type)
        IFieldRef *mkFieldRef(
                IExprIdP name,
                IDataTypeUserDefinedP type,
                bool is_input)
        IFunctionImportProto *mkFunctionImportProto(
                PlatQual plat,
                std_string lang,
                IFunctionPrototypeP proto)
        IFunctionImportType *mkFunctionImportType(
                PlatQual plat,
                std_string lang,
                ITypeIdentifierP type)
        IFunctionPrototype *mkFunctionPrototype(
                IExprIdP name,
                IDataTypeP rtype,
                bool is_target,
                bool is_solve)
        IGlobalScope *mkGlobalScope(
                int32_t fileid)
        IMonitorActivityActionTraversal *mkMonitorActivityActionTraversal(
                IExprRefPathP target,
                IConstraintStmtP with_c)
        IMonitorActivityConcat *mkMonitorActivityConcat(
                IMonitorActivityStmtP lhs,
                IMonitorActivityStmtP rhs)
        IMonitorActivityEventually *mkMonitorActivityEventually(
                IExprP condition,
                IMonitorActivityStmtP body)
        IMonitorActivityIfElse *mkMonitorActivityIfElse(
                IExprP cond,
                IMonitorActivityStmtP true_s,
                IMonitorActivityStmtP false_s)
        IMonitorActivityMatch *mkMonitorActivityMatch(
                IExprP cond)
        IMonitorActivityMonitorTraversal *mkMonitorActivityMonitorTraversal(
                IExprRefPathP target,
                IConstraintStmtP with_c)
        IMonitorActivityOverlap *mkMonitorActivityOverlap(
                IMonitorActivityStmtP lhs,
                IMonitorActivityStmtP rhs)
        IActivityActionHandleTraversal *mkActivityActionHandleTraversal(
                IExprRefPathContextP target,
                IConstraintStmtP with_c)
        IActivityActionTypeTraversal *mkActivityActionTypeTraversal(
                IDataTypeUserDefinedP target,
                IConstraintStmtP with_c)
        IActivityAtomicBlock *mkActivityAtomicBlock(
                IScopeChildP body)
        IActivityForeach *mkActivityForeach(
                IExprIdP it_id,
                IExprIdP idx_id,
                IExprRefPathContextP target,
                IScopeChildP body)
        IActivityIfElse *mkActivityIfElse(
                IExprP cond,
                IActivityStmtP true_s,
                IActivityStmtP false_s)
        IActivityMatch *mkActivityMatch(
                IExprP cond)
        IActivityRepeatCount *mkActivityRepeatCount(
                IExprIdP loop_var,
                IExprP count,
                IScopeChildP body)
        IActivityRepeatWhile *mkActivityRepeatWhile(
                IExprP cond,
                IScopeChildP body)
        IActivityReplicate *mkActivityReplicate(
                IExprIdP idx_id,
                IExprIdP it_label,
                IScopeChildP body)
        IActivitySelect *mkActivitySelect(
                )
        IProceduralStmtRepeatWhile *mkProceduralStmtRepeatWhile(
                IScopeChildP body,
                IExprP expr)
        IActivitySuper *mkActivitySuper(
                )
        IProceduralStmtWhile *mkProceduralStmtWhile(
                IScopeChildP body,
                IExprP expr)
        IConstraintBlock *mkConstraintBlock(
                std_string name,
                bool is_dynamic)
        IConstraintStmtForall *mkConstraintStmtForall(
                IExprIdP iterator_id,
                IDataTypeUserDefinedP type_id,
                IExprRefPathP ref_path)
        IConstraintStmtForeach *mkConstraintStmtForeach(
                IExprP expr)
        IConstraintStmtImplication *mkConstraintStmtImplication(
                IExprP cond)
        ISymbolScope *mkSymbolScope(
                std_string name)
        ITypeScope *mkTypeScope(
                IExprIdP name,
                ITypeIdentifierP super_t)
        IExprRefPathStaticFunc *mkExprRefPathStaticFunc(
                bool is_global,
                IMethodParameterListP params)
        IExprRefPathSuper *mkExprRefPathSuper(
                IExprHierarchicalIdP hier_id)
        IAction *mkAction(
                IExprIdP name,
                ITypeIdentifierP super_t,
                bool is_abstract)
        IMonitorActivitySchedule *mkMonitorActivitySchedule(
                std_string name)
        IMonitorActivitySequence *mkMonitorActivitySequence(
                std_string name)
        IActivityDecl *mkActivityDecl(
                std_string name)
        IRootSymbolScope *mkRootSymbolScope(
                std_string name)
        IStruct *mkStruct(
                IExprIdP name,
                ITypeIdentifierP super_t,
                StructKind kind)
        IConstraintSymbolScope *mkConstraintSymbolScope(
                std_string name)
        ISymbolEnumScope *mkSymbolEnumScope(
                std_string name)
        ISymbolExtendScope *mkSymbolExtendScope(
                std_string name)
        IActivityLabeledScope *mkActivityLabeledScope(
                std_string name)
        ISymbolFunctionScope *mkSymbolFunctionScope(
                std_string name)
        ISymbolTypeScope *mkSymbolTypeScope(
                std_string name,
                ISymbolScopeP plist)
        IMonitor *mkMonitor(
                IExprIdP name,
                ITypeIdentifierP super_t)
        IMonitorActivityDecl *mkMonitorActivityDecl(
                std_string name)
        IExecScope *mkExecScope(
                std_string name)
        IProceduralStmtSymbolBodyScope *mkProceduralStmtSymbolBodyScope(
                std_string name,
                IScopeChildP body)
        IComponent *mkComponent(
                IExprIdP name,
                ITypeIdentifierP super_t)
        IProceduralStmtRepeat *mkProceduralStmtRepeat(
                std_string name,
                IScopeChildP body,
                IExprIdP it_id,
                IExprP count)
        IActivityParallel *mkActivityParallel(
                std_string name,
                IActivityJoinSpecP join_spec)
        IProceduralStmtForeach *mkProceduralStmtForeach(
                std_string name,
                IScopeChildP body,
                IExprRefPathP path,
                IExprIdP it_id,
                IExprIdP idx_id)
        IActivitySchedule *mkActivitySchedule(
                std_string name,
                IActivityJoinSpecP join_spec)
        IExecBlock *mkExecBlock(
                std_string name,
                ExecKind kind)
        IActivitySequence *mkActivitySequence(
                std_string name)
cdef extern from "zsp/ast/IRefExpr.h" namespace "zsp::ast":
    cpdef cppclass IRefExpr:
        pass
        void accept(VisitorBase *v)

cdef extern from "zsp/ast/IExprAggrMapElem.h" namespace "zsp::ast":
    cpdef cppclass IExprAggrMapElem:
        IExpr *getLhs()
        
        void setLhs(IExpr *v)
        IExpr *getRhs()
        
        void setRhs(IExpr *v)
        void accept(VisitorBase *v)

cdef extern from "zsp/ast/IMonitorActivitySelectBranch.h" namespace "zsp::ast":
    cpdef cppclass IMonitorActivitySelectBranch:
        IExpr *getGuard()
        
        void setGuard(IExpr *v)
        IScopeChild *getBody()
        
        void setBody(IScopeChild *v)
        void accept(VisitorBase *v)

cdef extern from "zsp/ast/IExprAggrStructElem.h" namespace "zsp::ast":
    cpdef cppclass IExprAggrStructElem:
        IExprId *getName()
        
        void setName(IExprId *v)
        int32_t getTarget()
        
        void setTarget(int32_t v)
        IExpr *getValue()
        
        void setValue(IExpr *v)
        void accept(VisitorBase *v)

cdef extern from "zsp/ast/IScopeChild.h" namespace "zsp::ast":
    cpdef cppclass IScopeChild:
        const std_string &getDocstring()
        
        void setDocstring(const std_string & v)
        const Location & getLocation()
        
        void setLocation(const Location &)
        IScopeP getParent();
        
        void setParent(IScopeP v)
        int32_t getIndex()
        
        void setIndex(int32_t v)
        IAssocData *getAssocData()
        
        void setAssocData(IAssocData *v)
        void accept(VisitorBase *v)

cdef extern from "zsp/ast/IActivityJoinSpec.h" namespace "zsp::ast":
    cpdef cppclass IActivityJoinSpec:
        pass
        void accept(VisitorBase *v)

cdef extern from "zsp/ast/ISymbolImportSpec.h" namespace "zsp::ast":
    cpdef cppclass ISymbolImportSpec:
        std_vector[IPackageImportStmtP] & getImports();
        std_unordered_map[std_string,UP[ISymbolRefPath]] &getSymtab()
        void accept(VisitorBase *v)

cdef extern from "zsp/ast/ISymbolRefPath.h" namespace "zsp::ast":
    cpdef cppclass ISymbolRefPath:
        std_vector[SymbolRefPathElem] & getPath();
        int32_t getPyref_idx()
        
        void setPyref_idx(int32_t v)
        void accept(VisitorBase *v)

cdef extern from "zsp/ast/IActivityMatchChoice.h" namespace "zsp::ast":
    cpdef cppclass IActivityMatchChoice:
        bool getIs_default()
        
        void setIs_default(bool v)
        IExprOpenRangeList *getCond()
        
        void setCond(IExprOpenRangeList *v)
        IScopeChild *getBody()
        
        void setBody(IScopeChild *v)
        void accept(VisitorBase *v)

cdef extern from "zsp/ast/IAssocData.h" namespace "zsp::ast":
    cpdef cppclass IAssocData:
        pass
        void accept(VisitorBase *v)

cdef extern from "zsp/ast/IMonitorActivityMatchChoice.h" namespace "zsp::ast":
    cpdef cppclass IMonitorActivityMatchChoice:
        bool getIs_default()
        
        void setIs_default(bool v)
        IExprOpenRangeList *getCond()
        
        void setCond(IExprOpenRangeList *v)
        IScopeChild *getBody()
        
        void setBody(IScopeChild *v)
        void accept(VisitorBase *v)

cdef extern from "zsp/ast/ITemplateParamDeclList.h" namespace "zsp::ast":
    cpdef cppclass ITemplateParamDeclList:
        std_vector[UP[ITemplateParamDecl]] & getParams();
        bool getSpecialized()
        
        void setSpecialized(bool v)
        void accept(VisitorBase *v)

cdef extern from "zsp/ast/IActivitySelectBranch.h" namespace "zsp::ast":
    cpdef cppclass IActivitySelectBranch:
        IExpr *getGuard()
        
        void setGuard(IExpr *v)
        IExpr *getWeight()
        
        void setWeight(IExpr *v)
        IScopeChild *getBody()
        
        void setBody(IScopeChild *v)
        void accept(VisitorBase *v)

cdef extern from "zsp/ast/ITemplateParamValue.h" namespace "zsp::ast":
    cpdef cppclass ITemplateParamValue:
        pass
        void accept(VisitorBase *v)

cdef extern from "zsp/ast/ITemplateParamValueList.h" namespace "zsp::ast":
    cpdef cppclass ITemplateParamValueList:
        std_vector[UP[ITemplateParamValue]] & getValues();
        void accept(VisitorBase *v)

cdef extern from "zsp/ast/IExecTargetTemplateParam.h" namespace "zsp::ast":
    cpdef cppclass IExecTargetTemplateParam:
        IExpr *getExpr()
        
        void setExpr(IExpr *v)
        int32_t getStart()
        
        void setStart(int32_t v)
        int32_t getEnd()
        
        void setEnd(int32_t v)
        void accept(VisitorBase *v)

cdef extern from "zsp/ast/IExpr.h" namespace "zsp::ast":
    cpdef cppclass IExpr:
        pass
        void accept(VisitorBase *v)

cdef extern from "zsp/ast/IMonitorActivityStmt.h" namespace "zsp::ast":
    cpdef cppclass IMonitorActivityStmt(IScopeChild):
        pass

cdef extern from "zsp/ast/INamedScopeChild.h" namespace "zsp::ast":
    cpdef cppclass INamedScopeChild(IScopeChild):
        IExprId *getName()
        
        void setName(IExprId *v)

cdef extern from "zsp/ast/IActivityJoinSpecBranch.h" namespace "zsp::ast":
    cpdef cppclass IActivityJoinSpecBranch(IActivityJoinSpec):
        std_vector[UP[IExprRefPathContext]] & getBranches();

cdef extern from "zsp/ast/IActivityJoinSpecFirst.h" namespace "zsp::ast":
    cpdef cppclass IActivityJoinSpecFirst(IActivityJoinSpec):
        IExpr *getCount()
        
        void setCount(IExpr *v)

cdef extern from "zsp/ast/IActivityJoinSpecNone.h" namespace "zsp::ast":
    cpdef cppclass IActivityJoinSpecNone(IActivityJoinSpec):
        pass

cdef extern from "zsp/ast/IActivityJoinSpecSelect.h" namespace "zsp::ast":
    cpdef cppclass IActivityJoinSpecSelect(IActivityJoinSpec):
        IExpr *getCount()
        
        void setCount(IExpr *v)

cdef extern from "zsp/ast/IPackageImportStmt.h" namespace "zsp::ast":
    cpdef cppclass IPackageImportStmt(IScopeChild):
        bool getWildcard()
        
        void setWildcard(bool v)
        IExprId *getAlias()
        
        void setAlias(IExprId *v)
        ITypeIdentifier *getPath()
        
        void setPath(ITypeIdentifier *v)

cdef extern from "zsp/ast/IProceduralStmtIfClause.h" namespace "zsp::ast":
    cpdef cppclass IProceduralStmtIfClause(IScopeChild):
        IExpr *getCond()
        
        void setCond(IExpr *v)
        IScopeChild *getBody()
        
        void setBody(IScopeChild *v)

cdef extern from "zsp/ast/IActivitySchedulingConstraint.h" namespace "zsp::ast":
    cpdef cppclass IActivitySchedulingConstraint(IScopeChild):
        bool getIs_parallel()
        
        void setIs_parallel(bool v)
        std_vector[UP[IExprHierarchicalId]] & getTargets();

cdef extern from "zsp/ast/IActivityStmt.h" namespace "zsp::ast":
    cpdef cppclass IActivityStmt(IScopeChild):
        pass

cdef extern from "zsp/ast/IPyImportFromStmt.h" namespace "zsp::ast":
    cpdef cppclass IPyImportFromStmt(IScopeChild):
        std_vector[UP[IExprId]] & getPath();
        std_vector[UP[IExprId]] & getTargets();

cdef extern from "zsp/ast/IPyImportStmt.h" namespace "zsp::ast":
    cpdef cppclass IPyImportStmt(IScopeChild):
        std_vector[UP[IExprId]] & getPath();
        IExprId *getAlias()
        
        void setAlias(IExprId *v)

cdef extern from "zsp/ast/IConstraintStmt.h" namespace "zsp::ast":
    cpdef cppclass IConstraintStmt(IScopeChild):
        pass

cdef extern from "zsp/ast/IRefExprScopeIndex.h" namespace "zsp::ast":
    cpdef cppclass IRefExprScopeIndex(IRefExpr):
        IRefExpr *getBase()
        
        void setBase(IRefExpr *v)
        int32_t getOffset()
        
        void setOffset(int32_t v)

cdef extern from "zsp/ast/IRefExprTypeScopeContext.h" namespace "zsp::ast":
    cpdef cppclass IRefExprTypeScopeContext(IRefExpr):
        IRefExpr *getBase()
        
        void setBase(IRefExpr *v)
        int32_t getOffset()
        
        void setOffset(int32_t v)

cdef extern from "zsp/ast/IRefExprTypeScopeGlobal.h" namespace "zsp::ast":
    cpdef cppclass IRefExprTypeScopeGlobal(IRefExpr):
        int32_t getFileid()
        
        void setFileid(int32_t v)

cdef extern from "zsp/ast/IScope.h" namespace "zsp::ast":
    cpdef cppclass IScope(IScopeChild):
        const Location & getEndLocation()
        
        void setEndLocation(const Location &)
        std_vector[UP[IScopeChild]] & getChildren();

cdef extern from "zsp/ast/IScopeChildRef.h" namespace "zsp::ast":
    cpdef cppclass IScopeChildRef(IScopeChild):
        IScopeChildP getTarget();
        
        void setTarget(IScopeChildP v)

cdef extern from "zsp/ast/ISymbolChild.h" namespace "zsp::ast":
    cpdef cppclass ISymbolChild(IScopeChild):
        int32_t getId()
        
        void setId(int32_t v)
        ISymbolScopeP getUpper();
        
        void setUpper(ISymbolScopeP v)

cdef extern from "zsp/ast/ICoverStmtInline.h" namespace "zsp::ast":
    cpdef cppclass ICoverStmtInline(IScopeChild):
        IScopeChild *getBody()
        
        void setBody(IScopeChild *v)

cdef extern from "zsp/ast/ICoverStmtReference.h" namespace "zsp::ast":
    cpdef cppclass ICoverStmtReference(IScopeChild):
        IExprRefPath *getTarget()
        
        void setTarget(IExprRefPath *v)

cdef extern from "zsp/ast/IDataType.h" namespace "zsp::ast":
    cpdef cppclass IDataType(IScopeChild):
        pass

cdef extern from "zsp/ast/ISymbolScopeRef.h" namespace "zsp::ast":
    cpdef cppclass ISymbolScopeRef(IScopeChild):
        const std_string &getName()
        
        void setName(const std_string & v)

cdef extern from "zsp/ast/ITemplateParamDecl.h" namespace "zsp::ast":
    cpdef cppclass ITemplateParamDecl(IScopeChild):
        IExprId *getName()
        
        void setName(IExprId *v)

cdef extern from "zsp/ast/ITemplateParamExprValue.h" namespace "zsp::ast":
    cpdef cppclass ITemplateParamExprValue(ITemplateParamValue):
        IExpr *getValue()
        
        void setValue(IExpr *v)

cdef extern from "zsp/ast/ITemplateParamTypeValue.h" namespace "zsp::ast":
    cpdef cppclass ITemplateParamTypeValue(ITemplateParamValue):
        IDataType *getValue()
        
        void setValue(IDataType *v)

cdef extern from "zsp/ast/IExecStmt.h" namespace "zsp::ast":
    cpdef cppclass IExecStmt(IScopeChild):
        ISymbolScopeP getUpper();
        
        void setUpper(ISymbolScopeP v)

cdef extern from "zsp/ast/IExecTargetTemplateBlock.h" namespace "zsp::ast":
    cpdef cppclass IExecTargetTemplateBlock(IScopeChild):
        ExecKind getKind()
        
        void setKind(ExecKind v)
        const std_string &getData()
        
        void setData(const std_string & v)
        std_vector[UP[IExecTargetTemplateParam]] & getParameters();

cdef extern from "zsp/ast/ITypeIdentifier.h" namespace "zsp::ast":
    cpdef cppclass ITypeIdentifier(IExpr):
        std_vector[UP[ITypeIdentifierElem]] & getElems();
        ISymbolRefPath *getTarget()
        
        void setTarget(ISymbolRefPath *v)

cdef extern from "zsp/ast/ITypeIdentifierElem.h" namespace "zsp::ast":
    cpdef cppclass ITypeIdentifierElem(IExpr):
        IExprId *getId()
        
        void setId(IExprId *v)
        ITemplateParamValueList *getParams()
        
        void setParams(ITemplateParamValueList *v)

cdef extern from "zsp/ast/IExprAggrLiteral.h" namespace "zsp::ast":
    cpdef cppclass IExprAggrLiteral(IExpr):
        pass

cdef extern from "zsp/ast/IExprBin.h" namespace "zsp::ast":
    cpdef cppclass IExprBin(IExpr):
        IExpr *getLhs()
        
        void setLhs(IExpr *v)
        ExprBinOp getOp()
        
        void setOp(ExprBinOp v)
        IExpr *getRhs()
        
        void setRhs(IExpr *v)

cdef extern from "zsp/ast/IExprBitSlice.h" namespace "zsp::ast":
    cpdef cppclass IExprBitSlice(IExpr):
        IExpr *getLhs()
        
        void setLhs(IExpr *v)
        IExpr *getRhs()
        
        void setRhs(IExpr *v)

cdef extern from "zsp/ast/IExprBool.h" namespace "zsp::ast":
    cpdef cppclass IExprBool(IExpr):
        bool getValue()
        
        void setValue(bool v)

cdef extern from "zsp/ast/IExprCast.h" namespace "zsp::ast":
    cpdef cppclass IExprCast(IExpr):
        IDataType *getCasting_type()
        
        void setCasting_type(IDataType *v)
        IExpr *getExpr()
        
        void setExpr(IExpr *v)

cdef extern from "zsp/ast/IExprCompileHas.h" namespace "zsp::ast":
    cpdef cppclass IExprCompileHas(IExpr):
        IExprRefPathStatic *getRef()
        
        void setRef(IExprRefPathStatic *v)

cdef extern from "zsp/ast/IExprCond.h" namespace "zsp::ast":
    cpdef cppclass IExprCond(IExpr):
        IExpr *getCond_e()
        
        void setCond_e(IExpr *v)
        IExpr *getTrue_e()
        
        void setTrue_e(IExpr *v)
        IExpr *getFalse_e()
        
        void setFalse_e(IExpr *v)

cdef extern from "zsp/ast/IExprDomainOpenRangeList.h" namespace "zsp::ast":
    cpdef cppclass IExprDomainOpenRangeList(IExpr):
        std_vector[UP[IExprDomainOpenRangeValue]] & getValues();

cdef extern from "zsp/ast/IExprDomainOpenRangeValue.h" namespace "zsp::ast":
    cpdef cppclass IExprDomainOpenRangeValue(IExpr):
        bool getSingle()
        
        void setSingle(bool v)
        IExpr *getLhs()
        
        void setLhs(IExpr *v)
        IExpr *getRhs()
        
        void setRhs(IExpr *v)

cdef extern from "zsp/ast/IExprHierarchicalId.h" namespace "zsp::ast":
    cpdef cppclass IExprHierarchicalId(IExpr):
        std_vector[UP[IExprMemberPathElem]] & getElems();

cdef extern from "zsp/ast/IExprId.h" namespace "zsp::ast":
    cpdef cppclass IExprId(IExpr):
        const std_string &getId()
        
        void setId(const std_string & v)
        bool getIs_escaped()
        
        void setIs_escaped(bool v)
        const Location & getLocation()
        
        void setLocation(const Location &)

cdef extern from "zsp/ast/IExprIn.h" namespace "zsp::ast":
    cpdef cppclass IExprIn(IExpr):
        IExpr *getLhs()
        
        void setLhs(IExpr *v)
        IExprOpenRangeList *getRhs()
        
        void setRhs(IExprOpenRangeList *v)

cdef extern from "zsp/ast/IExprListLiteral.h" namespace "zsp::ast":
    cpdef cppclass IExprListLiteral(IExpr):
        std_vector[UP[IExpr]] & getValue();

cdef extern from "zsp/ast/IExprMemberPathElem.h" namespace "zsp::ast":
    cpdef cppclass IExprMemberPathElem(IExpr):
        IExprId *getId()
        
        void setId(IExprId *v)
        IMethodParameterList *getParams()
        
        void setParams(IMethodParameterList *v)
        std_vector[UP[IExpr]] & getSubscript();
        int32_t getTarget()
        
        void setTarget(int32_t v)
        int32_t getSuper()
        
        void setSuper(int32_t v)
        StringMethodId getString_method_id()
        
        void setString_method_id(StringMethodId v)

cdef extern from "zsp/ast/IExprNull.h" namespace "zsp::ast":
    cpdef cppclass IExprNull(IExpr):
        pass

cdef extern from "zsp/ast/IExprNumber.h" namespace "zsp::ast":
    cpdef cppclass IExprNumber(IExpr):
        pass

cdef extern from "zsp/ast/IExprOpenRangeList.h" namespace "zsp::ast":
    cpdef cppclass IExprOpenRangeList(IExpr):
        std_vector[UP[IExprOpenRangeValue]] & getValues();

cdef extern from "zsp/ast/IExprOpenRangeValue.h" namespace "zsp::ast":
    cpdef cppclass IExprOpenRangeValue(IExpr):
        IExpr *getLhs()
        
        void setLhs(IExpr *v)
        IExpr *getRhs()
        
        void setRhs(IExpr *v)

cdef extern from "zsp/ast/IExprRefPath.h" namespace "zsp::ast":
    cpdef cppclass IExprRefPath(IExpr):
        ISymbolRefPath *getTarget()
        
        void setTarget(ISymbolRefPath *v)

cdef extern from "zsp/ast/IExprRefPathElem.h" namespace "zsp::ast":
    cpdef cppclass IExprRefPathElem(IExpr):
        pass

cdef extern from "zsp/ast/IExprStaticRefPath.h" namespace "zsp::ast":
    cpdef cppclass IExprStaticRefPath(IExpr):
        bool getIs_global()
        
        void setIs_global(bool v)
        std_vector[UP[ITypeIdentifierElem]] & getBase();
        IExprMemberPathElem *getLeaf()
        
        void setLeaf(IExprMemberPathElem *v)

cdef extern from "zsp/ast/IExprString.h" namespace "zsp::ast":
    cpdef cppclass IExprString(IExpr):
        const std_string &getValue()
        
        void setValue(const std_string & v)
        bool getIs_raw()
        
        void setIs_raw(bool v)

cdef extern from "zsp/ast/IExprStructLiteral.h" namespace "zsp::ast":
    cpdef cppclass IExprStructLiteral(IExpr):
        std_vector[UP[IExprStructLiteralItem]] & getValues();

cdef extern from "zsp/ast/IExprStructLiteralItem.h" namespace "zsp::ast":
    cpdef cppclass IExprStructLiteralItem(IExpr):
        IExprId *getId()
        
        void setId(IExprId *v)
        IExpr *getValue()
        
        void setValue(IExpr *v)

cdef extern from "zsp/ast/IExprSubscript.h" namespace "zsp::ast":
    cpdef cppclass IExprSubscript(IExpr):
        IExpr *getExpr()
        
        void setExpr(IExpr *v)
        IExpr *getSubscript()
        
        void setSubscript(IExpr *v)

cdef extern from "zsp/ast/IExprSubstring.h" namespace "zsp::ast":
    cpdef cppclass IExprSubstring(IExpr):
        IExpr *getExpr()
        
        void setExpr(IExpr *v)
        IExpr *getStart()
        
        void setStart(IExpr *v)
        IExpr *getEnd()
        
        void setEnd(IExpr *v)

cdef extern from "zsp/ast/IExprUnary.h" namespace "zsp::ast":
    cpdef cppclass IExprUnary(IExpr):
        ExprUnaryOp getOp()
        
        void setOp(ExprUnaryOp v)
        IExpr *getRhs()
        
        void setRhs(IExpr *v)

cdef extern from "zsp/ast/IExtendEnum.h" namespace "zsp::ast":
    cpdef cppclass IExtendEnum(IScopeChild):
        ITypeIdentifier *getTarget()
        
        void setTarget(ITypeIdentifier *v)
        std_vector[UP[IEnumItem]] & getItems();

cdef extern from "zsp/ast/IFunctionDefinition.h" namespace "zsp::ast":
    cpdef cppclass IFunctionDefinition(IScopeChild):
        const Location & getEndLocation()
        
        void setEndLocation(const Location &)
        IFunctionPrototype *getProto()
        
        void setProto(IFunctionPrototype *v)
        IExecScope *getBody()
        
        void setBody(IExecScope *v)
        PlatQual getPlat()
        
        void setPlat(PlatQual v)

cdef extern from "zsp/ast/IFunctionImport.h" namespace "zsp::ast":
    cpdef cppclass IFunctionImport(IScopeChild):
        PlatQual getPlat()
        
        void setPlat(PlatQual v)
        const std_string &getLang()
        
        void setLang(const std_string & v)

cdef extern from "zsp/ast/IFunctionParamDecl.h" namespace "zsp::ast":
    cpdef cppclass IFunctionParamDecl(IScopeChild):
        FunctionParamDeclKind getKind()
        
        void setKind(FunctionParamDeclKind v)
        IExprId *getName()
        
        void setName(IExprId *v)
        IDataType *getType()
        
        void setType(IDataType *v)
        ParamDir getDir()
        
        void setDir(ParamDir v)
        IExpr *getDflt()
        
        void setDflt(IExpr *v)
        bool getIs_varargs()
        
        void setIs_varargs(bool v)

cdef extern from "zsp/ast/IMethodParameterList.h" namespace "zsp::ast":
    cpdef cppclass IMethodParameterList(IExpr):
        std_vector[UP[IExpr]] & getParameters();

cdef extern from "zsp/ast/IMonitorActivityRepeatCount.h" namespace "zsp::ast":
    cpdef cppclass IMonitorActivityRepeatCount(IMonitorActivityStmt):
        IExprId *getLoop_var()
        
        void setLoop_var(IExprId *v)
        IExpr *getCount()
        
        void setCount(IExpr *v)
        IScopeChild *getBody()
        
        void setBody(IScopeChild *v)

cdef extern from "zsp/ast/IMonitorActivityRepeatWhile.h" namespace "zsp::ast":
    cpdef cppclass IMonitorActivityRepeatWhile(IMonitorActivityStmt):
        IExpr *getCond()
        
        void setCond(IExpr *v)
        IScopeChild *getBody()
        
        void setBody(IScopeChild *v)

cdef extern from "zsp/ast/IMonitorActivitySelect.h" namespace "zsp::ast":
    cpdef cppclass IMonitorActivitySelect(IMonitorActivityStmt):
        IExprId *getLabel()
        
        void setLabel(IExprId *v)
        std_vector[UP[IMonitorActivitySelectBranch]] & getBranches();

cdef extern from "zsp/ast/IActivityBindStmt.h" namespace "zsp::ast":
    cpdef cppclass IActivityBindStmt(IActivityStmt):
        IExprHierarchicalId *getLhs()
        
        void setLhs(IExprHierarchicalId *v)
        std_vector[UP[IExprHierarchicalId]] & getRhs();

cdef extern from "zsp/ast/IActivityConstraint.h" namespace "zsp::ast":
    cpdef cppclass IActivityConstraint(IActivityStmt):
        IConstraintStmt *getConstraint()
        
        void setConstraint(IConstraintStmt *v)

cdef extern from "zsp/ast/IMonitorConstraint.h" namespace "zsp::ast":
    cpdef cppclass IMonitorConstraint(IMonitorActivityStmt):
        IConstraintStmt *getConstraint()
        
        void setConstraint(IConstraintStmt *v)

cdef extern from "zsp/ast/INamedScope.h" namespace "zsp::ast":
    cpdef cppclass INamedScope(IScope):
        IExprId *getName()
        
        void setName(IExprId *v)

cdef extern from "zsp/ast/IPackageScope.h" namespace "zsp::ast":
    cpdef cppclass IPackageScope(IScope):
        std_vector[UP[IExprId]] & getId();
        IPackageScopeP getSibling();
        
        void setSibling(IPackageScopeP v)

cdef extern from "zsp/ast/IProceduralStmtAssignment.h" namespace "zsp::ast":
    cpdef cppclass IProceduralStmtAssignment(IExecStmt):
        IExpr *getLhs()
        
        void setLhs(IExpr *v)
        AssignOp getOp()
        
        void setOp(AssignOp v)
        IExpr *getRhs()
        
        void setRhs(IExpr *v)

cdef extern from "zsp/ast/IProceduralStmtBody.h" namespace "zsp::ast":
    cpdef cppclass IProceduralStmtBody(IExecStmt):
        IScopeChild *getBody()
        
        void setBody(IScopeChild *v)

cdef extern from "zsp/ast/IProceduralStmtBreak.h" namespace "zsp::ast":
    cpdef cppclass IProceduralStmtBreak(IExecStmt):
        pass

cdef extern from "zsp/ast/IActivityLabeledStmt.h" namespace "zsp::ast":
    cpdef cppclass IActivityLabeledStmt(IActivityStmt):
        IExprId *getLabel()
        
        void setLabel(IExprId *v)

cdef extern from "zsp/ast/IProceduralStmtContinue.h" namespace "zsp::ast":
    cpdef cppclass IProceduralStmtContinue(IExecStmt):
        pass

cdef extern from "zsp/ast/IProceduralStmtDataDeclaration.h" namespace "zsp::ast":
    cpdef cppclass IProceduralStmtDataDeclaration(IExecStmt):
        IExprId *getName()
        
        void setName(IExprId *v)
        IDataType *getDatatype()
        
        void setDatatype(IDataType *v)
        IExpr *getInit()
        
        void setInit(IExpr *v)

cdef extern from "zsp/ast/IProceduralStmtExpr.h" namespace "zsp::ast":
    cpdef cppclass IProceduralStmtExpr(IExecStmt):
        IExpr *getExpr()
        
        void setExpr(IExpr *v)

cdef extern from "zsp/ast/IProceduralStmtFunctionCall.h" namespace "zsp::ast":
    cpdef cppclass IProceduralStmtFunctionCall(IExecStmt):
        IExprRefPathStaticRooted *getPrefix()
        
        void setPrefix(IExprRefPathStaticRooted *v)
        std_vector[UP[IExpr]] & getParams();

cdef extern from "zsp/ast/IProceduralStmtIfElse.h" namespace "zsp::ast":
    cpdef cppclass IProceduralStmtIfElse(IExecStmt):
        std_vector[UP[IProceduralStmtIfClause]] & getIf_then();
        IScopeChild *getElse_then()
        
        void setElse_then(IScopeChild *v)

cdef extern from "zsp/ast/IProceduralStmtMatch.h" namespace "zsp::ast":
    cpdef cppclass IProceduralStmtMatch(IExecStmt):
        IExpr *getExpr()
        
        void setExpr(IExpr *v)
        std_vector[UP[IProceduralStmtMatchChoice]] & getChoices();

cdef extern from "zsp/ast/IProceduralStmtMatchChoice.h" namespace "zsp::ast":
    cpdef cppclass IProceduralStmtMatchChoice(IExecStmt):
        bool getIs_default()
        
        void setIs_default(bool v)
        IExprOpenRangeList *getCond()
        
        void setCond(IExprOpenRangeList *v)
        IScopeChild *getBody()
        
        void setBody(IScopeChild *v)

cdef extern from "zsp/ast/IProceduralStmtRandomize.h" namespace "zsp::ast":
    cpdef cppclass IProceduralStmtRandomize(IExecStmt):
        IExpr *getTarget()
        
        void setTarget(IExpr *v)
        std_vector[UP[IConstraintStmt]] & getConstraints();

cdef extern from "zsp/ast/IProceduralStmtReturn.h" namespace "zsp::ast":
    cpdef cppclass IProceduralStmtReturn(IExecStmt):
        IExpr *getExpr()
        
        void setExpr(IExpr *v)

cdef extern from "zsp/ast/IProceduralStmtYield.h" namespace "zsp::ast":
    cpdef cppclass IProceduralStmtYield(IExecStmt):
        pass

cdef extern from "zsp/ast/IConstraintScope.h" namespace "zsp::ast":
    cpdef cppclass IConstraintScope(IConstraintStmt):
        const Location & getEndLocation()
        
        void setEndLocation(const Location &)
        std_vector[UP[IConstraintStmt]] & getConstraints();

cdef extern from "zsp/ast/IConstraintStmtDefault.h" namespace "zsp::ast":
    cpdef cppclass IConstraintStmtDefault(IConstraintStmt):
        IExprHierarchicalId *getHid()
        
        void setHid(IExprHierarchicalId *v)
        IExpr *getExpr()
        
        void setExpr(IExpr *v)

cdef extern from "zsp/ast/IConstraintStmtDefaultDisable.h" namespace "zsp::ast":
    cpdef cppclass IConstraintStmtDefaultDisable(IConstraintStmt):
        IExprHierarchicalId *getHid()
        
        void setHid(IExprHierarchicalId *v)

cdef extern from "zsp/ast/IConstraintStmtExpr.h" namespace "zsp::ast":
    cpdef cppclass IConstraintStmtExpr(IConstraintStmt):
        IExpr *getExpr()
        
        void setExpr(IExpr *v)

cdef extern from "zsp/ast/IConstraintStmtField.h" namespace "zsp::ast":
    cpdef cppclass IConstraintStmtField(IConstraintStmt):
        IExprId *getName()
        
        void setName(IExprId *v)
        IDataType *getType()
        
        void setType(IDataType *v)

cdef extern from "zsp/ast/IConstraintStmtIf.h" namespace "zsp::ast":
    cpdef cppclass IConstraintStmtIf(IConstraintStmt):
        IExpr *getCond()
        
        void setCond(IExpr *v)
        IConstraintScope *getTrue_c()
        
        void setTrue_c(IConstraintScope *v)
        IConstraintScope *getFalse_c()
        
        void setFalse_c(IConstraintScope *v)

cdef extern from "zsp/ast/IConstraintStmtUnique.h" namespace "zsp::ast":
    cpdef cppclass IConstraintStmtUnique(IConstraintStmt):
        std_vector[UP[IExprHierarchicalId]] & getList();

cdef extern from "zsp/ast/ISymbolChildrenScope.h" namespace "zsp::ast":
    cpdef cppclass ISymbolChildrenScope(ISymbolChild):
        const std_string &getName()
        
        void setName(const std_string & v)
        std_vector[UP[IScopeChild]] & getChildren();
        IScopeChildP getTarget();
        
        void setTarget(IScopeChildP v)

cdef extern from "zsp/ast/IDataTypeBool.h" namespace "zsp::ast":
    cpdef cppclass IDataTypeBool(IDataType):
        pass

cdef extern from "zsp/ast/IDataTypeChandle.h" namespace "zsp::ast":
    cpdef cppclass IDataTypeChandle(IDataType):
        pass

cdef extern from "zsp/ast/IDataTypeEnum.h" namespace "zsp::ast":
    cpdef cppclass IDataTypeEnum(IDataType):
        IDataTypeUserDefined *getTid()
        
        void setTid(IDataTypeUserDefined *v)
        IExprOpenRangeList *getIn_rangelist()
        
        void setIn_rangelist(IExprOpenRangeList *v)

cdef extern from "zsp/ast/IDataTypeInt.h" namespace "zsp::ast":
    cpdef cppclass IDataTypeInt(IDataType):
        bool getIs_signed()
        
        void setIs_signed(bool v)
        IExpr *getWidth()
        
        void setWidth(IExpr *v)
        IExprDomainOpenRangeList *getIn_range()
        
        void setIn_range(IExprDomainOpenRangeList *v)

cdef extern from "zsp/ast/IDataTypePyObj.h" namespace "zsp::ast":
    cpdef cppclass IDataTypePyObj(IDataType):
        pass

cdef extern from "zsp/ast/IDataTypeRef.h" namespace "zsp::ast":
    cpdef cppclass IDataTypeRef(IDataType):
        IDataTypeUserDefined *getType()
        
        void setType(IDataTypeUserDefined *v)

cdef extern from "zsp/ast/IDataTypeString.h" namespace "zsp::ast":
    cpdef cppclass IDataTypeString(IDataType):
        bool getHas_range()
        
        void setHas_range(bool v)
        std_vector[std_string] & getIn_range();

cdef extern from "zsp/ast/IDataTypeUserDefined.h" namespace "zsp::ast":
    cpdef cppclass IDataTypeUserDefined(IDataType):
        bool getIs_global()
        
        void setIs_global(bool v)
        ITypeIdentifier *getType_id()
        
        void setType_id(ITypeIdentifier *v)

cdef extern from "zsp/ast/IEnumDecl.h" namespace "zsp::ast":
    cpdef cppclass IEnumDecl(INamedScopeChild):
        std_vector[UP[IEnumItem]] & getItems();

cdef extern from "zsp/ast/IEnumItem.h" namespace "zsp::ast":
    cpdef cppclass IEnumItem(INamedScopeChild):
        IExpr *getValue()
        
        void setValue(IExpr *v)
        ISymbolEnumScopeP getUpper();
        
        void setUpper(ISymbolEnumScopeP v)

cdef extern from "zsp/ast/ITemplateCategoryTypeParamDecl.h" namespace "zsp::ast":
    cpdef cppclass ITemplateCategoryTypeParamDecl(ITemplateParamDecl):
        TypeCategory getCategory()
        
        void setCategory(TypeCategory v)
        ITypeIdentifier *getRestriction()
        
        void setRestriction(ITypeIdentifier *v)
        IDataType *getDflt()
        
        void setDflt(IDataType *v)

cdef extern from "zsp/ast/ITemplateGenericTypeParamDecl.h" namespace "zsp::ast":
    cpdef cppclass ITemplateGenericTypeParamDecl(ITemplateParamDecl):
        IDataType *getDflt()
        
        void setDflt(IDataType *v)

cdef extern from "zsp/ast/ITemplateValueParamDecl.h" namespace "zsp::ast":
    cpdef cppclass ITemplateValueParamDecl(ITemplateParamDecl):
        IDataType *getType()
        
        void setType(IDataType *v)
        IExpr *getDflt()
        
        void setDflt(IExpr *v)

cdef extern from "zsp/ast/IExprAggrEmpty.h" namespace "zsp::ast":
    cpdef cppclass IExprAggrEmpty(IExprAggrLiteral):
        pass

cdef extern from "zsp/ast/IExprAggrList.h" namespace "zsp::ast":
    cpdef cppclass IExprAggrList(IExprAggrLiteral):
        std_vector[UP[IExpr]] & getElems();

cdef extern from "zsp/ast/IExprAggrMap.h" namespace "zsp::ast":
    cpdef cppclass IExprAggrMap(IExprAggrLiteral):
        std_vector[UP[IExprAggrMapElem]] & getElems();

cdef extern from "zsp/ast/IExprAggrStruct.h" namespace "zsp::ast":
    cpdef cppclass IExprAggrStruct(IExprAggrLiteral):
        std_vector[UP[IExprAggrStructElem]] & getElems();

cdef extern from "zsp/ast/IExprRefPathContext.h" namespace "zsp::ast":
    cpdef cppclass IExprRefPathContext(IExprRefPath):
        bool getIs_super()
        
        void setIs_super(bool v)
        IExprHierarchicalId *getHier_id()
        
        void setHier_id(IExprHierarchicalId *v)
        IExprBitSlice *getSlice()
        
        void setSlice(IExprBitSlice *v)

cdef extern from "zsp/ast/IExprRefPathId.h" namespace "zsp::ast":
    cpdef cppclass IExprRefPathId(IExprRefPath):
        IExprId *getId()
        
        void setId(IExprId *v)
        IExprBitSlice *getSlice()
        
        void setSlice(IExprBitSlice *v)

cdef extern from "zsp/ast/IExprRefPathStatic.h" namespace "zsp::ast":
    cpdef cppclass IExprRefPathStatic(IExprRefPath):
        bool getIs_global()
        
        void setIs_global(bool v)
        std_vector[UP[ITypeIdentifierElem]] & getBase();
        IExprBitSlice *getSlice()
        
        void setSlice(IExprBitSlice *v)

cdef extern from "zsp/ast/IExprRefPathStaticRooted.h" namespace "zsp::ast":
    cpdef cppclass IExprRefPathStaticRooted(IExprRefPath):
        IExprRefPathStatic *getRoot()
        
        void setRoot(IExprRefPathStatic *v)
        IExprHierarchicalId *getLeaf()
        
        void setLeaf(IExprHierarchicalId *v)
        IExprBitSlice *getSlice()
        
        void setSlice(IExprBitSlice *v)

cdef extern from "zsp/ast/IExprSignedNumber.h" namespace "zsp::ast":
    cpdef cppclass IExprSignedNumber(IExprNumber):
        const std_string &getImage()
        
        void setImage(const std_string & v)
        int32_t getWidth()
        
        void setWidth(int32_t v)
        int64_t getValue()
        
        void setValue(int64_t v)

cdef extern from "zsp/ast/IExprUnsignedNumber.h" namespace "zsp::ast":
    cpdef cppclass IExprUnsignedNumber(IExprNumber):
        const std_string &getImage()
        
        void setImage(const std_string & v)
        int32_t getWidth()
        
        void setWidth(int32_t v)
        uint64_t getValue()
        
        void setValue(uint64_t v)

cdef extern from "zsp/ast/IExtendType.h" namespace "zsp::ast":
    cpdef cppclass IExtendType(IScope):
        ExtendTargetE getKind()
        
        void setKind(ExtendTargetE v)
        ITypeIdentifier *getTarget()
        
        void setTarget(ITypeIdentifier *v)
        std_unordered_map[std_string,int32_t] &getSymtab()
        ISymbolImportSpec *getImports()
        
        void setImports(ISymbolImportSpec *v)

cdef extern from "zsp/ast/IField.h" namespace "zsp::ast":
    cpdef cppclass IField(INamedScopeChild):
        IDataType *getType()
        
        void setType(IDataType *v)
        FieldAttr getAttr()
        
        void setAttr(FieldAttr v)
        IExpr *getInit()
        
        void setInit(IExpr *v)

cdef extern from "zsp/ast/IFieldClaim.h" namespace "zsp::ast":
    cpdef cppclass IFieldClaim(INamedScopeChild):
        IDataTypeUserDefined *getType()
        
        void setType(IDataTypeUserDefined *v)
        bool getIs_lock()
        
        void setIs_lock(bool v)

cdef extern from "zsp/ast/IFieldCompRef.h" namespace "zsp::ast":
    cpdef cppclass IFieldCompRef(INamedScopeChild):
        IDataTypeUserDefined *getType()
        
        void setType(IDataTypeUserDefined *v)

cdef extern from "zsp/ast/IFieldRef.h" namespace "zsp::ast":
    cpdef cppclass IFieldRef(INamedScopeChild):
        IDataTypeUserDefined *getType()
        
        void setType(IDataTypeUserDefined *v)
        bool getIs_input()
        
        void setIs_input(bool v)

cdef extern from "zsp/ast/IFunctionImportProto.h" namespace "zsp::ast":
    cpdef cppclass IFunctionImportProto(IFunctionImport):
        IFunctionPrototype *getProto()
        
        void setProto(IFunctionPrototype *v)

cdef extern from "zsp/ast/IFunctionImportType.h" namespace "zsp::ast":
    cpdef cppclass IFunctionImportType(IFunctionImport):
        ITypeIdentifier *getType()
        
        void setType(ITypeIdentifier *v)

cdef extern from "zsp/ast/IFunctionPrototype.h" namespace "zsp::ast":
    cpdef cppclass IFunctionPrototype(INamedScopeChild):
        IDataType *getRtype()
        
        void setRtype(IDataType *v)
        std_vector[UP[IFunctionParamDecl]] & getParameters();
        bool getIs_pure()
        
        void setIs_pure(bool v)
        bool getIs_target()
        
        void setIs_target(bool v)
        bool getIs_solve()
        
        void setIs_solve(bool v)
        bool getIs_core()
        
        void setIs_core(bool v)

cdef extern from "zsp/ast/IGlobalScope.h" namespace "zsp::ast":
    cpdef cppclass IGlobalScope(IScope):
        int32_t getFileid()
        
        void setFileid(int32_t v)
        const std_string &getFilename()
        
        void setFilename(const std_string & v)

cdef extern from "zsp/ast/IMonitorActivityActionTraversal.h" namespace "zsp::ast":
    cpdef cppclass IMonitorActivityActionTraversal(IMonitorActivityStmt):
        IExprRefPath *getTarget()
        
        void setTarget(IExprRefPath *v)
        IConstraintStmt *getWith_c()
        
        void setWith_c(IConstraintStmt *v)

cdef extern from "zsp/ast/IMonitorActivityConcat.h" namespace "zsp::ast":
    cpdef cppclass IMonitorActivityConcat(IMonitorActivityStmt):
        IMonitorActivityStmt *getLhs()
        
        void setLhs(IMonitorActivityStmt *v)
        IMonitorActivityStmt *getRhs()
        
        void setRhs(IMonitorActivityStmt *v)

cdef extern from "zsp/ast/IMonitorActivityEventually.h" namespace "zsp::ast":
    cpdef cppclass IMonitorActivityEventually(IMonitorActivityStmt):
        IExpr *getCondition()
        
        void setCondition(IExpr *v)
        IMonitorActivityStmt *getBody()
        
        void setBody(IMonitorActivityStmt *v)

cdef extern from "zsp/ast/IMonitorActivityIfElse.h" namespace "zsp::ast":
    cpdef cppclass IMonitorActivityIfElse(IMonitorActivityStmt):
        IExpr *getCond()
        
        void setCond(IExpr *v)
        IMonitorActivityStmt *getTrue_s()
        
        void setTrue_s(IMonitorActivityStmt *v)
        IMonitorActivityStmt *getFalse_s()
        
        void setFalse_s(IMonitorActivityStmt *v)

cdef extern from "zsp/ast/IMonitorActivityMatch.h" namespace "zsp::ast":
    cpdef cppclass IMonitorActivityMatch(IMonitorActivityStmt):
        IExpr *getCond()
        
        void setCond(IExpr *v)
        std_vector[UP[IMonitorActivityMatchChoice]] & getChoices();

cdef extern from "zsp/ast/IMonitorActivityMonitorTraversal.h" namespace "zsp::ast":
    cpdef cppclass IMonitorActivityMonitorTraversal(IMonitorActivityStmt):
        IExprRefPath *getTarget()
        
        void setTarget(IExprRefPath *v)
        IConstraintStmt *getWith_c()
        
        void setWith_c(IConstraintStmt *v)

cdef extern from "zsp/ast/IMonitorActivityOverlap.h" namespace "zsp::ast":
    cpdef cppclass IMonitorActivityOverlap(IMonitorActivityStmt):
        IMonitorActivityStmt *getLhs()
        
        void setLhs(IMonitorActivityStmt *v)
        IMonitorActivityStmt *getRhs()
        
        void setRhs(IMonitorActivityStmt *v)

cdef extern from "zsp/ast/IActivityActionHandleTraversal.h" namespace "zsp::ast":
    cpdef cppclass IActivityActionHandleTraversal(IActivityLabeledStmt):
        IExprRefPathContext *getTarget()
        
        void setTarget(IExprRefPathContext *v)
        IConstraintStmt *getWith_c()
        
        void setWith_c(IConstraintStmt *v)

cdef extern from "zsp/ast/IActivityActionTypeTraversal.h" namespace "zsp::ast":
    cpdef cppclass IActivityActionTypeTraversal(IActivityLabeledStmt):
        IDataTypeUserDefined *getTarget()
        
        void setTarget(IDataTypeUserDefined *v)
        IConstraintStmt *getWith_c()
        
        void setWith_c(IConstraintStmt *v)

cdef extern from "zsp/ast/IActivityAtomicBlock.h" namespace "zsp::ast":
    cpdef cppclass IActivityAtomicBlock(IActivityLabeledStmt):
        IScopeChild *getBody()
        
        void setBody(IScopeChild *v)

cdef extern from "zsp/ast/IActivityForeach.h" namespace "zsp::ast":
    cpdef cppclass IActivityForeach(IActivityLabeledStmt):
        IExprId *getIt_id()
        
        void setIt_id(IExprId *v)
        IExprId *getIdx_id()
        
        void setIdx_id(IExprId *v)
        IExprRefPathContext *getTarget()
        
        void setTarget(IExprRefPathContext *v)
        IScopeChild *getBody()
        
        void setBody(IScopeChild *v)

cdef extern from "zsp/ast/IActivityIfElse.h" namespace "zsp::ast":
    cpdef cppclass IActivityIfElse(IActivityLabeledStmt):
        IExpr *getCond()
        
        void setCond(IExpr *v)
        IActivityStmt *getTrue_s()
        
        void setTrue_s(IActivityStmt *v)
        IActivityStmt *getFalse_s()
        
        void setFalse_s(IActivityStmt *v)

cdef extern from "zsp/ast/IActivityMatch.h" namespace "zsp::ast":
    cpdef cppclass IActivityMatch(IActivityLabeledStmt):
        IExpr *getCond()
        
        void setCond(IExpr *v)
        std_vector[UP[IActivityMatchChoice]] & getChoices();

cdef extern from "zsp/ast/IActivityRepeatCount.h" namespace "zsp::ast":
    cpdef cppclass IActivityRepeatCount(IActivityLabeledStmt):
        IExprId *getLoop_var()
        
        void setLoop_var(IExprId *v)
        IExpr *getCount()
        
        void setCount(IExpr *v)
        IScopeChild *getBody()
        
        void setBody(IScopeChild *v)

cdef extern from "zsp/ast/IActivityRepeatWhile.h" namespace "zsp::ast":
    cpdef cppclass IActivityRepeatWhile(IActivityLabeledStmt):
        IExpr *getCond()
        
        void setCond(IExpr *v)
        IScopeChild *getBody()
        
        void setBody(IScopeChild *v)

cdef extern from "zsp/ast/IActivityReplicate.h" namespace "zsp::ast":
    cpdef cppclass IActivityReplicate(IActivityLabeledStmt):
        IExprId *getIdx_id()
        
        void setIdx_id(IExprId *v)
        IExprId *getIt_label()
        
        void setIt_label(IExprId *v)
        IScopeChild *getBody()
        
        void setBody(IScopeChild *v)

cdef extern from "zsp/ast/IActivitySelect.h" namespace "zsp::ast":
    cpdef cppclass IActivitySelect(IActivityLabeledStmt):
        std_vector[UP[IActivitySelectBranch]] & getBranches();

cdef extern from "zsp/ast/IProceduralStmtRepeatWhile.h" namespace "zsp::ast":
    cpdef cppclass IProceduralStmtRepeatWhile(IProceduralStmtBody):
        IExpr *getExpr()
        
        void setExpr(IExpr *v)

cdef extern from "zsp/ast/IActivitySuper.h" namespace "zsp::ast":
    cpdef cppclass IActivitySuper(IActivityLabeledStmt):
        pass

cdef extern from "zsp/ast/IProceduralStmtWhile.h" namespace "zsp::ast":
    cpdef cppclass IProceduralStmtWhile(IProceduralStmtBody):
        IExpr *getExpr()
        
        void setExpr(IExpr *v)

cdef extern from "zsp/ast/IConstraintBlock.h" namespace "zsp::ast":
    cpdef cppclass IConstraintBlock(IConstraintScope):
        const std_string &getName()
        
        void setName(const std_string & v)
        bool getIs_dynamic()
        
        void setIs_dynamic(bool v)

cdef extern from "zsp/ast/IConstraintStmtForall.h" namespace "zsp::ast":
    cpdef cppclass IConstraintStmtForall(IConstraintScope):
        IExprId *getIterator_id()
        
        void setIterator_id(IExprId *v)
        IDataTypeUserDefined *getType_id()
        
        void setType_id(IDataTypeUserDefined *v)
        IExprRefPath *getRef_path()
        
        void setRef_path(IExprRefPath *v)
        IConstraintSymbolScope *getSymtab()
        
        void setSymtab(IConstraintSymbolScope *v)

cdef extern from "zsp/ast/IConstraintStmtForeach.h" namespace "zsp::ast":
    cpdef cppclass IConstraintStmtForeach(IConstraintScope):
        IConstraintStmtFieldP getIt();
        
        void setIt(IConstraintStmtFieldP v)
        IConstraintStmtFieldP getIdx();
        
        void setIdx(IConstraintStmtFieldP v)
        IExpr *getExpr()
        
        void setExpr(IExpr *v)
        IConstraintSymbolScope *getSymtab()
        
        void setSymtab(IConstraintSymbolScope *v)

cdef extern from "zsp/ast/IConstraintStmtImplication.h" namespace "zsp::ast":
    cpdef cppclass IConstraintStmtImplication(IConstraintScope):
        IExpr *getCond()
        
        void setCond(IExpr *v)

cdef extern from "zsp/ast/ISymbolScope.h" namespace "zsp::ast":
    cpdef cppclass ISymbolScope(ISymbolChildrenScope):
        std_unordered_map[std_string,int32_t] &getSymtab()
        ISymbolImportSpec *getImports()
        
        void setImports(ISymbolImportSpec *v)
        bool getSynthetic()
        
        void setSynthetic(bool v)
        bool getOpaque()
        
        void setOpaque(bool v)

cdef extern from "zsp/ast/ITypeScope.h" namespace "zsp::ast":
    cpdef cppclass ITypeScope(INamedScope):
        ITypeIdentifier *getSuper_t()
        
        void setSuper_t(ITypeIdentifier *v)
        ITemplateParamDeclList *getParams()
        
        void setParams(ITemplateParamDeclList *v)
        bool getOpaque()
        
        void setOpaque(bool v)

cdef extern from "zsp/ast/IExprRefPathStaticFunc.h" namespace "zsp::ast":
    cpdef cppclass IExprRefPathStaticFunc(IExprRefPathStatic):
        IMethodParameterList *getParams()
        
        void setParams(IMethodParameterList *v)

cdef extern from "zsp/ast/IExprRefPathSuper.h" namespace "zsp::ast":
    cpdef cppclass IExprRefPathSuper(IExprRefPathContext):
        pass

cdef extern from "zsp/ast/IAction.h" namespace "zsp::ast":
    cpdef cppclass IAction(ITypeScope):
        bool getIs_abstract()
        
        void setIs_abstract(bool v)

cdef extern from "zsp/ast/IMonitorActivitySchedule.h" namespace "zsp::ast":
    cpdef cppclass IMonitorActivitySchedule(ISymbolScope):
        IExprId *getLabel()
        
        void setLabel(IExprId *v)

cdef extern from "zsp/ast/IMonitorActivitySequence.h" namespace "zsp::ast":
    cpdef cppclass IMonitorActivitySequence(ISymbolScope):
        IExprId *getLabel()
        
        void setLabel(IExprId *v)

cdef extern from "zsp/ast/IActivityDecl.h" namespace "zsp::ast":
    cpdef cppclass IActivityDecl(ISymbolScope):
        pass

cdef extern from "zsp/ast/IRootSymbolScope.h" namespace "zsp::ast":
    cpdef cppclass IRootSymbolScope(ISymbolScope):
        std_vector[UP[IGlobalScope]] & getUnits();
        std_unordered_map[int32_t,std_string] &getFilenames()
        std_unordered_map[int32_t,int32_t] &getId2idx()
        std_vector[std_vector[int32_t]] & getFileOutRef();
        std_vector[std_vector[int32_t]] & getFileInRef();

cdef extern from "zsp/ast/IStruct.h" namespace "zsp::ast":
    cpdef cppclass IStruct(ITypeScope):
        StructKind getKind()
        
        void setKind(StructKind v)

cdef extern from "zsp/ast/IConstraintSymbolScope.h" namespace "zsp::ast":
    cpdef cppclass IConstraintSymbolScope(ISymbolScope):
        IConstraintStmtP getConstraint();
        
        void setConstraint(IConstraintStmtP v)

cdef extern from "zsp/ast/ISymbolEnumScope.h" namespace "zsp::ast":
    cpdef cppclass ISymbolEnumScope(ISymbolScope):
        pass

cdef extern from "zsp/ast/ISymbolExtendScope.h" namespace "zsp::ast":
    cpdef cppclass ISymbolExtendScope(ISymbolScope):
        pass

cdef extern from "zsp/ast/IActivityLabeledScope.h" namespace "zsp::ast":
    cpdef cppclass IActivityLabeledScope(ISymbolScope):
        IExprId *getLabel()
        
        void setLabel(IExprId *v)

cdef extern from "zsp/ast/ISymbolFunctionScope.h" namespace "zsp::ast":
    cpdef cppclass ISymbolFunctionScope(ISymbolScope):
        std_vector[IFunctionPrototypeP] & getPrototypes();
        std_vector[UP[IFunctionImport]] & getImport_specs();
        IFunctionDefinitionP getDefinition();
        
        void setDefinition(IFunctionDefinitionP v)
        ISymbolScope *getPlist()
        
        void setPlist(ISymbolScope *v)
        IExecScopeP getBody();
        
        void setBody(IExecScopeP v)

cdef extern from "zsp/ast/ISymbolTypeScope.h" namespace "zsp::ast":
    cpdef cppclass ISymbolTypeScope(ISymbolScope):
        ISymbolScope *getPlist()
        
        void setPlist(ISymbolScope *v)
        std_vector[UP[ISymbolTypeScope]] & getSpec_types();

cdef extern from "zsp/ast/IMonitor.h" namespace "zsp::ast":
    cpdef cppclass IMonitor(ITypeScope):
        bool getIs_abstract()
        
        void setIs_abstract(bool v)

cdef extern from "zsp/ast/IMonitorActivityDecl.h" namespace "zsp::ast":
    cpdef cppclass IMonitorActivityDecl(ISymbolScope):
        pass

cdef extern from "zsp/ast/IExecScope.h" namespace "zsp::ast":
    cpdef cppclass IExecScope(ISymbolScope):
        const Location & getEndLocation()
        
        void setEndLocation(const Location &)

cdef extern from "zsp/ast/IProceduralStmtSymbolBodyScope.h" namespace "zsp::ast":
    cpdef cppclass IProceduralStmtSymbolBodyScope(ISymbolScope):
        IScopeChild *getBody()
        
        void setBody(IScopeChild *v)

cdef extern from "zsp/ast/IComponent.h" namespace "zsp::ast":
    cpdef cppclass IComponent(ITypeScope):
        pass

cdef extern from "zsp/ast/IProceduralStmtRepeat.h" namespace "zsp::ast":
    cpdef cppclass IProceduralStmtRepeat(IProceduralStmtSymbolBodyScope):
        IExprId *getIt_id()
        
        void setIt_id(IExprId *v)
        IExpr *getCount()
        
        void setCount(IExpr *v)

cdef extern from "zsp/ast/IActivityParallel.h" namespace "zsp::ast":
    cpdef cppclass IActivityParallel(IActivityLabeledScope):
        IActivityJoinSpec *getJoin_spec()
        
        void setJoin_spec(IActivityJoinSpec *v)

cdef extern from "zsp/ast/IProceduralStmtForeach.h" namespace "zsp::ast":
    cpdef cppclass IProceduralStmtForeach(IProceduralStmtSymbolBodyScope):
        IExprRefPath *getPath()
        
        void setPath(IExprRefPath *v)
        IExprId *getIt_id()
        
        void setIt_id(IExprId *v)
        IExprId *getIdx_id()
        
        void setIdx_id(IExprId *v)

cdef extern from "zsp/ast/IActivitySchedule.h" namespace "zsp::ast":
    cpdef cppclass IActivitySchedule(IActivityLabeledScope):
        IActivityJoinSpec *getJoin_spec()
        
        void setJoin_spec(IActivityJoinSpec *v)

cdef extern from "zsp/ast/IExecBlock.h" namespace "zsp::ast":
    cpdef cppclass IExecBlock(IExecScope):
        ExecKind getKind()
        
        void setKind(ExecKind v)

cdef extern from "zsp/ast/IActivitySequence.h" namespace "zsp::ast":
    cpdef cppclass IActivitySequence(IActivityLabeledScope):
        pass

cdef extern from 'zsp/ast/impl/VisitorBase.h' namespace 'zsp::ast':
    cpdef cppclass VisitorBase:
        void visitRefExpr(IRefExprP i)
        void visitExprAggrMapElem(IExprAggrMapElemP i)
        void visitMonitorActivitySelectBranch(IMonitorActivitySelectBranchP i)
        void visitExprAggrStructElem(IExprAggrStructElemP i)
        void visitScopeChild(IScopeChildP i)
        void visitActivityJoinSpec(IActivityJoinSpecP i)
        void visitSymbolImportSpec(ISymbolImportSpecP i)
        void visitSymbolRefPath(ISymbolRefPathP i)
        void visitActivityMatchChoice(IActivityMatchChoiceP i)
        void visitAssocData(IAssocDataP i)
        void visitMonitorActivityMatchChoice(IMonitorActivityMatchChoiceP i)
        void visitTemplateParamDeclList(ITemplateParamDeclListP i)
        void visitActivitySelectBranch(IActivitySelectBranchP i)
        void visitTemplateParamValue(ITemplateParamValueP i)
        void visitTemplateParamValueList(ITemplateParamValueListP i)
        void visitExecTargetTemplateParam(IExecTargetTemplateParamP i)
        void visitExpr(IExprP i)
        void visitMonitorActivityStmt(IMonitorActivityStmtP i)
        void visitNamedScopeChild(INamedScopeChildP i)
        void visitActivityJoinSpecBranch(IActivityJoinSpecBranchP i)
        void visitActivityJoinSpecFirst(IActivityJoinSpecFirstP i)
        void visitActivityJoinSpecNone(IActivityJoinSpecNoneP i)
        void visitActivityJoinSpecSelect(IActivityJoinSpecSelectP i)
        void visitPackageImportStmt(IPackageImportStmtP i)
        void visitProceduralStmtIfClause(IProceduralStmtIfClauseP i)
        void visitActivitySchedulingConstraint(IActivitySchedulingConstraintP i)
        void visitActivityStmt(IActivityStmtP i)
        void visitPyImportFromStmt(IPyImportFromStmtP i)
        void visitPyImportStmt(IPyImportStmtP i)
        void visitConstraintStmt(IConstraintStmtP i)
        void visitRefExprScopeIndex(IRefExprScopeIndexP i)
        void visitRefExprTypeScopeContext(IRefExprTypeScopeContextP i)
        void visitRefExprTypeScopeGlobal(IRefExprTypeScopeGlobalP i)
        void visitScope(IScopeP i)
        void visitScopeChildRef(IScopeChildRefP i)
        void visitSymbolChild(ISymbolChildP i)
        void visitCoverStmtInline(ICoverStmtInlineP i)
        void visitCoverStmtReference(ICoverStmtReferenceP i)
        void visitDataType(IDataTypeP i)
        void visitSymbolScopeRef(ISymbolScopeRefP i)
        void visitTemplateParamDecl(ITemplateParamDeclP i)
        void visitTemplateParamExprValue(ITemplateParamExprValueP i)
        void visitTemplateParamTypeValue(ITemplateParamTypeValueP i)
        void visitExecStmt(IExecStmtP i)
        void visitExecTargetTemplateBlock(IExecTargetTemplateBlockP i)
        void visitTypeIdentifier(ITypeIdentifierP i)
        void visitTypeIdentifierElem(ITypeIdentifierElemP i)
        void visitExprAggrLiteral(IExprAggrLiteralP i)
        void visitExprBin(IExprBinP i)
        void visitExprBitSlice(IExprBitSliceP i)
        void visitExprBool(IExprBoolP i)
        void visitExprCast(IExprCastP i)
        void visitExprCompileHas(IExprCompileHasP i)
        void visitExprCond(IExprCondP i)
        void visitExprDomainOpenRangeList(IExprDomainOpenRangeListP i)
        void visitExprDomainOpenRangeValue(IExprDomainOpenRangeValueP i)
        void visitExprHierarchicalId(IExprHierarchicalIdP i)
        void visitExprId(IExprIdP i)
        void visitExprIn(IExprInP i)
        void visitExprListLiteral(IExprListLiteralP i)
        void visitExprMemberPathElem(IExprMemberPathElemP i)
        void visitExprNull(IExprNullP i)
        void visitExprNumber(IExprNumberP i)
        void visitExprOpenRangeList(IExprOpenRangeListP i)
        void visitExprOpenRangeValue(IExprOpenRangeValueP i)
        void visitExprRefPath(IExprRefPathP i)
        void visitExprRefPathElem(IExprRefPathElemP i)
        void visitExprStaticRefPath(IExprStaticRefPathP i)
        void visitExprString(IExprStringP i)
        void visitExprStructLiteral(IExprStructLiteralP i)
        void visitExprStructLiteralItem(IExprStructLiteralItemP i)
        void visitExprSubscript(IExprSubscriptP i)
        void visitExprSubstring(IExprSubstringP i)
        void visitExprUnary(IExprUnaryP i)
        void visitExtendEnum(IExtendEnumP i)
        void visitFunctionDefinition(IFunctionDefinitionP i)
        void visitFunctionImport(IFunctionImportP i)
        void visitFunctionParamDecl(IFunctionParamDeclP i)
        void visitMethodParameterList(IMethodParameterListP i)
        void visitMonitorActivityRepeatCount(IMonitorActivityRepeatCountP i)
        void visitMonitorActivityRepeatWhile(IMonitorActivityRepeatWhileP i)
        void visitMonitorActivitySelect(IMonitorActivitySelectP i)
        void visitActivityBindStmt(IActivityBindStmtP i)
        void visitActivityConstraint(IActivityConstraintP i)
        void visitMonitorConstraint(IMonitorConstraintP i)
        void visitNamedScope(INamedScopeP i)
        void visitPackageScope(IPackageScopeP i)
        void visitProceduralStmtAssignment(IProceduralStmtAssignmentP i)
        void visitProceduralStmtBody(IProceduralStmtBodyP i)
        void visitProceduralStmtBreak(IProceduralStmtBreakP i)
        void visitActivityLabeledStmt(IActivityLabeledStmtP i)
        void visitProceduralStmtContinue(IProceduralStmtContinueP i)
        void visitProceduralStmtDataDeclaration(IProceduralStmtDataDeclarationP i)
        void visitProceduralStmtExpr(IProceduralStmtExprP i)
        void visitProceduralStmtFunctionCall(IProceduralStmtFunctionCallP i)
        void visitProceduralStmtIfElse(IProceduralStmtIfElseP i)
        void visitProceduralStmtMatch(IProceduralStmtMatchP i)
        void visitProceduralStmtMatchChoice(IProceduralStmtMatchChoiceP i)
        void visitProceduralStmtRandomize(IProceduralStmtRandomizeP i)
        void visitProceduralStmtReturn(IProceduralStmtReturnP i)
        void visitProceduralStmtYield(IProceduralStmtYieldP i)
        void visitConstraintScope(IConstraintScopeP i)
        void visitConstraintStmtDefault(IConstraintStmtDefaultP i)
        void visitConstraintStmtDefaultDisable(IConstraintStmtDefaultDisableP i)
        void visitConstraintStmtExpr(IConstraintStmtExprP i)
        void visitConstraintStmtField(IConstraintStmtFieldP i)
        void visitConstraintStmtIf(IConstraintStmtIfP i)
        void visitConstraintStmtUnique(IConstraintStmtUniqueP i)
        void visitSymbolChildrenScope(ISymbolChildrenScopeP i)
        void visitDataTypeBool(IDataTypeBoolP i)
        void visitDataTypeChandle(IDataTypeChandleP i)
        void visitDataTypeEnum(IDataTypeEnumP i)
        void visitDataTypeInt(IDataTypeIntP i)
        void visitDataTypePyObj(IDataTypePyObjP i)
        void visitDataTypeRef(IDataTypeRefP i)
        void visitDataTypeString(IDataTypeStringP i)
        void visitDataTypeUserDefined(IDataTypeUserDefinedP i)
        void visitEnumDecl(IEnumDeclP i)
        void visitEnumItem(IEnumItemP i)
        void visitTemplateCategoryTypeParamDecl(ITemplateCategoryTypeParamDeclP i)
        void visitTemplateGenericTypeParamDecl(ITemplateGenericTypeParamDeclP i)
        void visitTemplateValueParamDecl(ITemplateValueParamDeclP i)
        void visitExprAggrEmpty(IExprAggrEmptyP i)
        void visitExprAggrList(IExprAggrListP i)
        void visitExprAggrMap(IExprAggrMapP i)
        void visitExprAggrStruct(IExprAggrStructP i)
        void visitExprRefPathContext(IExprRefPathContextP i)
        void visitExprRefPathId(IExprRefPathIdP i)
        void visitExprRefPathStatic(IExprRefPathStaticP i)
        void visitExprRefPathStaticRooted(IExprRefPathStaticRootedP i)
        void visitExprSignedNumber(IExprSignedNumberP i)
        void visitExprUnsignedNumber(IExprUnsignedNumberP i)
        void visitExtendType(IExtendTypeP i)
        void visitField(IFieldP i)
        void visitFieldClaim(IFieldClaimP i)
        void visitFieldCompRef(IFieldCompRefP i)
        void visitFieldRef(IFieldRefP i)
        void visitFunctionImportProto(IFunctionImportProtoP i)
        void visitFunctionImportType(IFunctionImportTypeP i)
        void visitFunctionPrototype(IFunctionPrototypeP i)
        void visitGlobalScope(IGlobalScopeP i)
        void visitMonitorActivityActionTraversal(IMonitorActivityActionTraversalP i)
        void visitMonitorActivityConcat(IMonitorActivityConcatP i)
        void visitMonitorActivityEventually(IMonitorActivityEventuallyP i)
        void visitMonitorActivityIfElse(IMonitorActivityIfElseP i)
        void visitMonitorActivityMatch(IMonitorActivityMatchP i)
        void visitMonitorActivityMonitorTraversal(IMonitorActivityMonitorTraversalP i)
        void visitMonitorActivityOverlap(IMonitorActivityOverlapP i)
        void visitActivityActionHandleTraversal(IActivityActionHandleTraversalP i)
        void visitActivityActionTypeTraversal(IActivityActionTypeTraversalP i)
        void visitActivityAtomicBlock(IActivityAtomicBlockP i)
        void visitActivityForeach(IActivityForeachP i)
        void visitActivityIfElse(IActivityIfElseP i)
        void visitActivityMatch(IActivityMatchP i)
        void visitActivityRepeatCount(IActivityRepeatCountP i)
        void visitActivityRepeatWhile(IActivityRepeatWhileP i)
        void visitActivityReplicate(IActivityReplicateP i)
        void visitActivitySelect(IActivitySelectP i)
        void visitProceduralStmtRepeatWhile(IProceduralStmtRepeatWhileP i)
        void visitActivitySuper(IActivitySuperP i)
        void visitProceduralStmtWhile(IProceduralStmtWhileP i)
        void visitConstraintBlock(IConstraintBlockP i)
        void visitConstraintStmtForall(IConstraintStmtForallP i)
        void visitConstraintStmtForeach(IConstraintStmtForeachP i)
        void visitConstraintStmtImplication(IConstraintStmtImplicationP i)
        void visitSymbolScope(ISymbolScopeP i)
        void visitTypeScope(ITypeScopeP i)
        void visitExprRefPathStaticFunc(IExprRefPathStaticFuncP i)
        void visitExprRefPathSuper(IExprRefPathSuperP i)
        void visitAction(IActionP i)
        void visitMonitorActivitySchedule(IMonitorActivityScheduleP i)
        void visitMonitorActivitySequence(IMonitorActivitySequenceP i)
        void visitActivityDecl(IActivityDeclP i)
        void visitRootSymbolScope(IRootSymbolScopeP i)
        void visitStruct(IStructP i)
        void visitConstraintSymbolScope(IConstraintSymbolScopeP i)
        void visitSymbolEnumScope(ISymbolEnumScopeP i)
        void visitSymbolExtendScope(ISymbolExtendScopeP i)
        void visitActivityLabeledScope(IActivityLabeledScopeP i)
        void visitSymbolFunctionScope(ISymbolFunctionScopeP i)
        void visitSymbolTypeScope(ISymbolTypeScopeP i)
        void visitMonitor(IMonitorP i)
        void visitMonitorActivityDecl(IMonitorActivityDeclP i)
        void visitExecScope(IExecScopeP i)
        void visitProceduralStmtSymbolBodyScope(IProceduralStmtSymbolBodyScopeP i)
        void visitComponent(IComponentP i)
        void visitProceduralStmtRepeat(IProceduralStmtRepeatP i)
        void visitActivityParallel(IActivityParallelP i)
        void visitProceduralStmtForeach(IProceduralStmtForeachP i)
        void visitActivitySchedule(IActivityScheduleP i)
        void visitExecBlock(IExecBlockP i)
        void visitActivitySequence(IActivitySequenceP i)
cdef extern from 'PyBaseVisitor.h' namespace 'zsp::ast':
    cpdef cppclass PyBaseVisitor(VisitorBase):
        PyBaseVisitor(cpy_ref.PyObject *)
        void py_acceptRefExpr(IRefExpr *i);
        void py_acceptExprAggrMapElem(IExprAggrMapElem *i);
        void py_acceptMonitorActivitySelectBranch(IMonitorActivitySelectBranch *i);
        void py_acceptExprAggrStructElem(IExprAggrStructElem *i);
        void py_acceptScopeChild(IScopeChild *i);
        void py_acceptActivityJoinSpec(IActivityJoinSpec *i);
        void py_acceptSymbolImportSpec(ISymbolImportSpec *i);
        void py_acceptSymbolRefPath(ISymbolRefPath *i);
        void py_acceptActivityMatchChoice(IActivityMatchChoice *i);
        void py_acceptAssocData(IAssocData *i);
        void py_acceptMonitorActivityMatchChoice(IMonitorActivityMatchChoice *i);
        void py_acceptTemplateParamDeclList(ITemplateParamDeclList *i);
        void py_acceptActivitySelectBranch(IActivitySelectBranch *i);
        void py_acceptTemplateParamValue(ITemplateParamValue *i);
        void py_acceptTemplateParamValueList(ITemplateParamValueList *i);
        void py_acceptExecTargetTemplateParam(IExecTargetTemplateParam *i);
        void py_acceptExpr(IExpr *i);
        void py_visitRefExprBase(IRefExpr *i)
        void py_visitExprAggrMapElemBase(IExprAggrMapElem *i)
        void py_visitMonitorActivitySelectBranchBase(IMonitorActivitySelectBranch *i)
        void py_visitExprAggrStructElemBase(IExprAggrStructElem *i)
        void py_visitScopeChildBase(IScopeChild *i)
        void py_visitActivityJoinSpecBase(IActivityJoinSpec *i)
        void py_visitSymbolImportSpecBase(ISymbolImportSpec *i)
        void py_visitSymbolRefPathBase(ISymbolRefPath *i)
        void py_visitActivityMatchChoiceBase(IActivityMatchChoice *i)
        void py_visitAssocDataBase(IAssocData *i)
        void py_visitMonitorActivityMatchChoiceBase(IMonitorActivityMatchChoice *i)
        void py_visitTemplateParamDeclListBase(ITemplateParamDeclList *i)
        void py_visitActivitySelectBranchBase(IActivitySelectBranch *i)
        void py_visitTemplateParamValueBase(ITemplateParamValue *i)
        void py_visitTemplateParamValueListBase(ITemplateParamValueList *i)
        void py_visitExecTargetTemplateParamBase(IExecTargetTemplateParam *i)
        void py_visitExprBase(IExpr *i)
        void py_visitMonitorActivityStmtBase(IMonitorActivityStmt *i)
        void py_visitNamedScopeChildBase(INamedScopeChild *i)
        void py_visitActivityJoinSpecBranchBase(IActivityJoinSpecBranch *i)
        void py_visitActivityJoinSpecFirstBase(IActivityJoinSpecFirst *i)
        void py_visitActivityJoinSpecNoneBase(IActivityJoinSpecNone *i)
        void py_visitActivityJoinSpecSelectBase(IActivityJoinSpecSelect *i)
        void py_visitPackageImportStmtBase(IPackageImportStmt *i)
        void py_visitProceduralStmtIfClauseBase(IProceduralStmtIfClause *i)
        void py_visitActivitySchedulingConstraintBase(IActivitySchedulingConstraint *i)
        void py_visitActivityStmtBase(IActivityStmt *i)
        void py_visitPyImportFromStmtBase(IPyImportFromStmt *i)
        void py_visitPyImportStmtBase(IPyImportStmt *i)
        void py_visitConstraintStmtBase(IConstraintStmt *i)
        void py_visitRefExprScopeIndexBase(IRefExprScopeIndex *i)
        void py_visitRefExprTypeScopeContextBase(IRefExprTypeScopeContext *i)
        void py_visitRefExprTypeScopeGlobalBase(IRefExprTypeScopeGlobal *i)
        void py_visitScopeBase(IScope *i)
        void py_visitScopeChildRefBase(IScopeChildRef *i)
        void py_visitSymbolChildBase(ISymbolChild *i)
        void py_visitCoverStmtInlineBase(ICoverStmtInline *i)
        void py_visitCoverStmtReferenceBase(ICoverStmtReference *i)
        void py_visitDataTypeBase(IDataType *i)
        void py_visitSymbolScopeRefBase(ISymbolScopeRef *i)
        void py_visitTemplateParamDeclBase(ITemplateParamDecl *i)
        void py_visitTemplateParamExprValueBase(ITemplateParamExprValue *i)
        void py_visitTemplateParamTypeValueBase(ITemplateParamTypeValue *i)
        void py_visitExecStmtBase(IExecStmt *i)
        void py_visitExecTargetTemplateBlockBase(IExecTargetTemplateBlock *i)
        void py_visitTypeIdentifierBase(ITypeIdentifier *i)
        void py_visitTypeIdentifierElemBase(ITypeIdentifierElem *i)
        void py_visitExprAggrLiteralBase(IExprAggrLiteral *i)
        void py_visitExprBinBase(IExprBin *i)
        void py_visitExprBitSliceBase(IExprBitSlice *i)
        void py_visitExprBoolBase(IExprBool *i)
        void py_visitExprCastBase(IExprCast *i)
        void py_visitExprCompileHasBase(IExprCompileHas *i)
        void py_visitExprCondBase(IExprCond *i)
        void py_visitExprDomainOpenRangeListBase(IExprDomainOpenRangeList *i)
        void py_visitExprDomainOpenRangeValueBase(IExprDomainOpenRangeValue *i)
        void py_visitExprHierarchicalIdBase(IExprHierarchicalId *i)
        void py_visitExprIdBase(IExprId *i)
        void py_visitExprInBase(IExprIn *i)
        void py_visitExprListLiteralBase(IExprListLiteral *i)
        void py_visitExprMemberPathElemBase(IExprMemberPathElem *i)
        void py_visitExprNullBase(IExprNull *i)
        void py_visitExprNumberBase(IExprNumber *i)
        void py_visitExprOpenRangeListBase(IExprOpenRangeList *i)
        void py_visitExprOpenRangeValueBase(IExprOpenRangeValue *i)
        void py_visitExprRefPathBase(IExprRefPath *i)
        void py_visitExprRefPathElemBase(IExprRefPathElem *i)
        void py_visitExprStaticRefPathBase(IExprStaticRefPath *i)
        void py_visitExprStringBase(IExprString *i)
        void py_visitExprStructLiteralBase(IExprStructLiteral *i)
        void py_visitExprStructLiteralItemBase(IExprStructLiteralItem *i)
        void py_visitExprSubscriptBase(IExprSubscript *i)
        void py_visitExprSubstringBase(IExprSubstring *i)
        void py_visitExprUnaryBase(IExprUnary *i)
        void py_visitExtendEnumBase(IExtendEnum *i)
        void py_visitFunctionDefinitionBase(IFunctionDefinition *i)
        void py_visitFunctionImportBase(IFunctionImport *i)
        void py_visitFunctionParamDeclBase(IFunctionParamDecl *i)
        void py_visitMethodParameterListBase(IMethodParameterList *i)
        void py_visitMonitorActivityRepeatCountBase(IMonitorActivityRepeatCount *i)
        void py_visitMonitorActivityRepeatWhileBase(IMonitorActivityRepeatWhile *i)
        void py_visitMonitorActivitySelectBase(IMonitorActivitySelect *i)
        void py_visitActivityBindStmtBase(IActivityBindStmt *i)
        void py_visitActivityConstraintBase(IActivityConstraint *i)
        void py_visitMonitorConstraintBase(IMonitorConstraint *i)
        void py_visitNamedScopeBase(INamedScope *i)
        void py_visitPackageScopeBase(IPackageScope *i)
        void py_visitProceduralStmtAssignmentBase(IProceduralStmtAssignment *i)
        void py_visitProceduralStmtBodyBase(IProceduralStmtBody *i)
        void py_visitProceduralStmtBreakBase(IProceduralStmtBreak *i)
        void py_visitActivityLabeledStmtBase(IActivityLabeledStmt *i)
        void py_visitProceduralStmtContinueBase(IProceduralStmtContinue *i)
        void py_visitProceduralStmtDataDeclarationBase(IProceduralStmtDataDeclaration *i)
        void py_visitProceduralStmtExprBase(IProceduralStmtExpr *i)
        void py_visitProceduralStmtFunctionCallBase(IProceduralStmtFunctionCall *i)
        void py_visitProceduralStmtIfElseBase(IProceduralStmtIfElse *i)
        void py_visitProceduralStmtMatchBase(IProceduralStmtMatch *i)
        void py_visitProceduralStmtMatchChoiceBase(IProceduralStmtMatchChoice *i)
        void py_visitProceduralStmtRandomizeBase(IProceduralStmtRandomize *i)
        void py_visitProceduralStmtReturnBase(IProceduralStmtReturn *i)
        void py_visitProceduralStmtYieldBase(IProceduralStmtYield *i)
        void py_visitConstraintScopeBase(IConstraintScope *i)
        void py_visitConstraintStmtDefaultBase(IConstraintStmtDefault *i)
        void py_visitConstraintStmtDefaultDisableBase(IConstraintStmtDefaultDisable *i)
        void py_visitConstraintStmtExprBase(IConstraintStmtExpr *i)
        void py_visitConstraintStmtFieldBase(IConstraintStmtField *i)
        void py_visitConstraintStmtIfBase(IConstraintStmtIf *i)
        void py_visitConstraintStmtUniqueBase(IConstraintStmtUnique *i)
        void py_visitSymbolChildrenScopeBase(ISymbolChildrenScope *i)
        void py_visitDataTypeBoolBase(IDataTypeBool *i)
        void py_visitDataTypeChandleBase(IDataTypeChandle *i)
        void py_visitDataTypeEnumBase(IDataTypeEnum *i)
        void py_visitDataTypeIntBase(IDataTypeInt *i)
        void py_visitDataTypePyObjBase(IDataTypePyObj *i)
        void py_visitDataTypeRefBase(IDataTypeRef *i)
        void py_visitDataTypeStringBase(IDataTypeString *i)
        void py_visitDataTypeUserDefinedBase(IDataTypeUserDefined *i)
        void py_visitEnumDeclBase(IEnumDecl *i)
        void py_visitEnumItemBase(IEnumItem *i)
        void py_visitTemplateCategoryTypeParamDeclBase(ITemplateCategoryTypeParamDecl *i)
        void py_visitTemplateGenericTypeParamDeclBase(ITemplateGenericTypeParamDecl *i)
        void py_visitTemplateValueParamDeclBase(ITemplateValueParamDecl *i)
        void py_visitExprAggrEmptyBase(IExprAggrEmpty *i)
        void py_visitExprAggrListBase(IExprAggrList *i)
        void py_visitExprAggrMapBase(IExprAggrMap *i)
        void py_visitExprAggrStructBase(IExprAggrStruct *i)
        void py_visitExprRefPathContextBase(IExprRefPathContext *i)
        void py_visitExprRefPathIdBase(IExprRefPathId *i)
        void py_visitExprRefPathStaticBase(IExprRefPathStatic *i)
        void py_visitExprRefPathStaticRootedBase(IExprRefPathStaticRooted *i)
        void py_visitExprSignedNumberBase(IExprSignedNumber *i)
        void py_visitExprUnsignedNumberBase(IExprUnsignedNumber *i)
        void py_visitExtendTypeBase(IExtendType *i)
        void py_visitFieldBase(IField *i)
        void py_visitFieldClaimBase(IFieldClaim *i)
        void py_visitFieldCompRefBase(IFieldCompRef *i)
        void py_visitFieldRefBase(IFieldRef *i)
        void py_visitFunctionImportProtoBase(IFunctionImportProto *i)
        void py_visitFunctionImportTypeBase(IFunctionImportType *i)
        void py_visitFunctionPrototypeBase(IFunctionPrototype *i)
        void py_visitGlobalScopeBase(IGlobalScope *i)
        void py_visitMonitorActivityActionTraversalBase(IMonitorActivityActionTraversal *i)
        void py_visitMonitorActivityConcatBase(IMonitorActivityConcat *i)
        void py_visitMonitorActivityEventuallyBase(IMonitorActivityEventually *i)
        void py_visitMonitorActivityIfElseBase(IMonitorActivityIfElse *i)
        void py_visitMonitorActivityMatchBase(IMonitorActivityMatch *i)
        void py_visitMonitorActivityMonitorTraversalBase(IMonitorActivityMonitorTraversal *i)
        void py_visitMonitorActivityOverlapBase(IMonitorActivityOverlap *i)
        void py_visitActivityActionHandleTraversalBase(IActivityActionHandleTraversal *i)
        void py_visitActivityActionTypeTraversalBase(IActivityActionTypeTraversal *i)
        void py_visitActivityAtomicBlockBase(IActivityAtomicBlock *i)
        void py_visitActivityForeachBase(IActivityForeach *i)
        void py_visitActivityIfElseBase(IActivityIfElse *i)
        void py_visitActivityMatchBase(IActivityMatch *i)
        void py_visitActivityRepeatCountBase(IActivityRepeatCount *i)
        void py_visitActivityRepeatWhileBase(IActivityRepeatWhile *i)
        void py_visitActivityReplicateBase(IActivityReplicate *i)
        void py_visitActivitySelectBase(IActivitySelect *i)
        void py_visitProceduralStmtRepeatWhileBase(IProceduralStmtRepeatWhile *i)
        void py_visitActivitySuperBase(IActivitySuper *i)
        void py_visitProceduralStmtWhileBase(IProceduralStmtWhile *i)
        void py_visitConstraintBlockBase(IConstraintBlock *i)
        void py_visitConstraintStmtForallBase(IConstraintStmtForall *i)
        void py_visitConstraintStmtForeachBase(IConstraintStmtForeach *i)
        void py_visitConstraintStmtImplicationBase(IConstraintStmtImplication *i)
        void py_visitSymbolScopeBase(ISymbolScope *i)
        void py_visitTypeScopeBase(ITypeScope *i)
        void py_visitExprRefPathStaticFuncBase(IExprRefPathStaticFunc *i)
        void py_visitExprRefPathSuperBase(IExprRefPathSuper *i)
        void py_visitActionBase(IAction *i)
        void py_visitMonitorActivityScheduleBase(IMonitorActivitySchedule *i)
        void py_visitMonitorActivitySequenceBase(IMonitorActivitySequence *i)
        void py_visitActivityDeclBase(IActivityDecl *i)
        void py_visitRootSymbolScopeBase(IRootSymbolScope *i)
        void py_visitStructBase(IStruct *i)
        void py_visitConstraintSymbolScopeBase(IConstraintSymbolScope *i)
        void py_visitSymbolEnumScopeBase(ISymbolEnumScope *i)
        void py_visitSymbolExtendScopeBase(ISymbolExtendScope *i)
        void py_visitActivityLabeledScopeBase(IActivityLabeledScope *i)
        void py_visitSymbolFunctionScopeBase(ISymbolFunctionScope *i)
        void py_visitSymbolTypeScopeBase(ISymbolTypeScope *i)
        void py_visitMonitorBase(IMonitor *i)
        void py_visitMonitorActivityDeclBase(IMonitorActivityDecl *i)
        void py_visitExecScopeBase(IExecScope *i)
        void py_visitProceduralStmtSymbolBodyScopeBase(IProceduralStmtSymbolBodyScope *i)
        void py_visitComponentBase(IComponent *i)
        void py_visitProceduralStmtRepeatBase(IProceduralStmtRepeat *i)
        void py_visitActivityParallelBase(IActivityParallel *i)
        void py_visitProceduralStmtForeachBase(IProceduralStmtForeach *i)
        void py_visitActivityScheduleBase(IActivitySchedule *i)
        void py_visitExecBlockBase(IExecBlock *i)
        void py_visitActivitySequenceBase(IActivitySequence *i)
