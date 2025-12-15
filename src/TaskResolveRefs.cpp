/*
 * TaskResolveRefs.cpp
 *
 * Copyright 2022 Matthew Ballance and Contributors
 *
 * Licensed under the Apache License, Version 2.0 (the "License"); you may 
 * not use this file except in compliance with the License.  
 * You may obtain a copy of the License at:
 *
 *   http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software 
 * distributed under the License is distributed on an "AS IS" BASIS, 
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.  
 * See the License for the specific language governing permissions and 
 * limitations under the License.
 *
 * Created on:
 *     Author:
 */
#include <set>
#include "dmgr/impl/DebugMacros.h"
#include "TaskFindPathElem.h"
#include "TaskLinkActionCompRefFields.h"
#include "TaskResolveImports.h"
#include "TaskResolveRef.h"
#include "TaskResolveRefs.h"
#include "TaskSpecializeParameterizedRef.h"
#include "zsp/parser/impl/TaskResolveSymbolPathRef.h"
#include "zsp/parser/impl/TaskGetElemSymbolScope.h"
#include "zsp/parser/impl/TaskGetSubscriptSymbolScope.h"
#include "zsp/parser/impl/TaskIsPyRef.h"

namespace zsp {
namespace parser {



TaskResolveRefs::TaskResolveRefs(ResolveContext *ctxt) : TaskResolveBase(ctxt) {
    DEBUG_INIT("TaskResolveRefs", ctxt->getDebugMgr());
}

TaskResolveRefs::~TaskResolveRefs() {

}

void TaskResolveRefs::resolve(ast::ISymbolScope *root) {
    DEBUG_ENTER("resolve (SymbolScope root) %d %p (%s)", 
        root->getSymtab().size(), 
        root,
        root->getName().c_str());
//    m_root = root;
    m_ctxt->pushSymtab(m_ctxt->getFactory()->mkAstSymbolTableIterator(root));

    // First, ensure all actions have their 'comp' refs updated
    // Should this be done at root level?
    TaskLinkActionCompRefFields(m_ctxt->getFactory()).link(root);

    // Phases:
    // - 

    if (root->getImports()) {
        DEBUG_ENTER("  Resolve Imports");
        TaskResolveImports(m_ctxt).resolve(root);
        DEBUG_LEAVE("  Resolve Imports");
    }

    DEBUG("resolve ==> process children");
    for (std::vector<ast::IScopeChildUP>::const_iterator
        it=root->getChildren().begin();
        it!=root->getChildren().end(); it++) {
        it->get()->accept(this);
    }
    DEBUG("resolve <== process children");

    m_ctxt->popSymtab();

    DEBUG_LEAVE("resolve");
}

void TaskResolveRefs::resolve(ast::ISymbolTypeScope *scope) {
    DEBUG_ENTER("resolve (iterator, scope) %s", scope->getName().c_str());

    if (scope->getPlist()) {
        DEBUG_ENTER("Resolving names in plist");
        scope->getPlist()->accept(m_this);
        DEBUG_LEAVE("Resolving names in plist");
    }

    ast::ITypeScope *target_s = dynamic_cast<ast::ITypeScope *>(scope->getTarget());
    if (target_s->getSuper_t()) {
        target_s->getSuper_t()->accept(m_this);
    }

    // Create an iterator based on the type-scope itself
    ISymbolTableIterator *type_it = TaskResolveSymbolPathRef(
        m_ctxt->getDebugMgr(),
        m_ctxt->root()).mkIterator(
            m_ctxt->getFactory()->mkAstSymbolTableIterator(m_ctxt->root()),
            scope);
    // Remove the type itself, since this will be added 
    // during resolution
    type_it->popScope();

    // Is this required here?
    DEBUG("Pushing symbol iterator for body");
    m_ctxt->pushSymtab(type_it);

    ast::SymbolRefPathElemKind kind = ast::SymbolRefPathElemKind::ElemKind_ChildIdx;

    ast::ITypeScope *i_ts = dynamic_cast<ast::ITypeScope *>(scope->getTarget());
    if (i_ts->getParams() && i_ts->getParams()->getSpecialized()) {
            kind = ast::SymbolRefPathElemKind::ElemKind_TypeSpec;
            DEBUG("Processing specialization depth=%d", m_ctxt->specializationDepth());

            // TODO: need a way to detect that we have a superseding 
            // scope stack, so we don't redo it

            // Create a symbol-table iterator that:
            // - starts with m_root
            // - is preloaded with the scopes of the target type

            // if (m_ctxt->specializationDepth() == 1) {
            //     DEBUG("Updating resolution stack to use local scope");
            //     m_ctxt->pushSymtab(TaskResolveSymbolPathRef(
            //         m_ctxt->getDebugMgr(), m_ctxt->root()).mkIterator(
            //             m_ctxt->getFactory()->mkAstSymbolTableIterator(m_ctxt->root()),
            //             i));
            // } else {
            //     DEBUG("Retaining existing resolution stack");
            // }
            // // TODO: need to resolve refs in the parameter list
            // // relative to the containing type
            // // Ensure parameter references are resolved
            // DEBUG_ENTER("Resolve refs in parameter decl list");
            // i_ts->getParams()->accept(m_this);
            // DEBUG_LEAVE("Resolve refs in parameter decl list");
            // if (m_ctxt->specializationDepth() == 1) {
            //     m_ctxt->popSymtab();
            // }
        }

    m_ctxt->symtab()->pushScope(scope, kind);

    TaskLinkActionCompRefFields(m_ctxt->getFactory()).link(scope);

    // Check on children
    for (std::vector<ast::IScopeChildUP>::const_iterator
        it=scope->getChildren().begin();
        it!=scope->getChildren().end(); it++) {
        it->get()->accept(m_this);
    }

    m_ctxt->symtab()->popScope();

    DEBUG("Removing symbol iterator for body");
    m_ctxt->popSymtab();

    DEBUG_LEAVE("resolve (iterator, scope)");
}

void TaskResolveRefs::visitActivityActionHandleTraversal(ast::IActivityActionHandleTraversal *i) {
    DEBUG_ENTER("visitActivityActionHandleTraversal");
    ast::ISymbolRefPath *target_ref = TaskResolveRef(m_ctxt).resolve(i->getTarget());

    if (!target_ref) {
        return;
    }

    i->getTarget()->setTarget(target_ref);
    ast::IScopeChild *target = resolvePath(i->getTarget()->getTarget());

    if (target) {
        m_ctxt->addRef(i->getLocation().fileid, target->getLocation().fileid);
    }

    ast::IField *field = dynamic_cast<ast::IField *>(target);
    DEBUG("target=%p field=%p", target, field);
    DEBUG("field: %s", field->getName()->getId().c_str());
    ast::IDataType *field_t = field->getType();
    ast::IDataTypeUserDefined *field_udt = dynamic_cast<ast::IDataTypeUserDefined *>(field_t);

    DEBUG("field_t=%p action_t=%p", field_t, field_udt);
    ast::IScopeChild *field_c = resolvePath(field_udt->getType_id()->getTarget());
    ast::ISymbolScope *field_scope = dynamic_cast<ast::ISymbolScope *>(field_c);
    DEBUG("field_c=%p field_scope=%s", field_c, field_scope->getName().c_str());
    if (i->getWith_c()) {
        m_ctxt->symtab()->pushScope(field_scope, ast::SymbolRefPathElemKind::ElemKind_Inline);
        m_ctxt->pushInlineCtxt(field_scope);
        DEBUG_ENTER(" ::getWith()");
        i->getWith_c()->accept(m_this);
        DEBUG_LEAVE(" ::getWith()");
        m_ctxt->popInlineCtxt();
        m_ctxt->symtab()->popScope();
    }
    DEBUG_LEAVE("visitActivityActionHandleTraversal");
}
    
void TaskResolveRefs::visitActivityActionTypeTraversal(ast::IActivityActionTypeTraversal *i) {
    DEBUG_ENTER("visitActivityActionTypeTraversal");
    i->getTarget()->accept(m_this);
    ast::IDataTypeUserDefined *field_udt = i->getTarget(); // <ast::IDataTypeUserDefined *>(i->getTarget());
//    DEBUG("--> resolve field_udt->getType_id()");
//    field_udt->getType_id()->accept(m_this);
//    DEBUG("<-- resolve field_udt->getType_id()");
//    ast::IScopeChild *field_c = resolvePath(field_udt->getType_id()->getTarget());
    if (field_udt->getType_id()->getTarget()) {
        ast::IScopeChild *field_c = resolvePath(field_udt->getType_id()->getTarget());
        ast::ISymbolScope *field_scope = dynamic_cast<ast::ISymbolScope *>(field_c);
        if (i->getWith_c()) {
            m_ctxt->symtab()->pushScope(field_scope, ast::SymbolRefPathElemKind::ElemKind_Inline);
            m_ctxt->pushInlineCtxt(field_scope);
            DEBUG_ENTER(" ::getWith()");
            i->getWith_c()->accept(m_this);
            DEBUG_LEAVE(" ::getWith()");
            m_ctxt->popInlineCtxt();
            m_ctxt->symtab()->popScope();
        }
    }
    DEBUG_LEAVE("visitActivityActionTypeTraversal");
}

void TaskResolveRefs::visitConstraintBlock(ast::IConstraintBlock *i) {
    DEBUG_ENTER("visitConstraintBlock (idx=%d)", i->getIndex());
    m_ctxt->symtab()->pushScope(i);
    VisitorBase::visitConstraintBlock(i);
    m_ctxt->symtab()->popScope();
    DEBUG_LEAVE("visitConstraintBlock");
}

void TaskResolveRefs::visitConstraintStmtForeach(ast::IConstraintStmtForeach *i) {
    DEBUG_ENTER("visitConstraintStmtForeach %d", i->getSymtab()->getSymtab().size());
    // Resolve symbols in the array path
    i->getExpr()->accept(m_this);

    m_ctxt->symtab()->pushScope(i->getSymtab());
    for (std::vector<ast::IConstraintStmtUP>::const_iterator
        it=i->getConstraints().begin();
        it!=i->getConstraints().end(); it++) {
        (*it)->accept(m_this);
    }
    m_ctxt->symtab()->popScope();
    DEBUG_LEAVE("visitConstraintStmtForeach");
}

void TaskResolveRefs::visitExecScope(ast::IExecScope *i) {
    DEBUG_ENTER("visitExecScope");
    m_ctxt->symtab()->pushScope(i);
    for (std::vector<ast::IScopeChildUP>::const_iterator
        it=i->getChildren().begin();
        it!=i->getChildren().end(); it++) {
        (*it)->accept(m_this);
    }
    m_ctxt->symtab()->popScope();
    DEBUG_LEAVE("visitExecScope");
}

void TaskResolveRefs::visitExprRefPathContext(ast::IExprRefPathContext *i) {
    DEBUG_ENTER("visitExprRefPathContext %s", i->getHier_id()->getElems().at(0)->getId()->getId().c_str());
    // Find the first path element
    ast::ISymbolRefPath *target = TaskResolveRef(m_ctxt).resolve(
        i->getHier_id()->getElems().at(0)->getId());

    if (!target) {
        m_ctxt->addMarker(
            MarkerSeverityE::Error,
            i->getHier_id()->getElems().at(0)->getId()->getLocation(),
            "failed to find root ref-path element %s",
            i->getHier_id()->getElems().at(0)->getId()->getId().c_str());

        DEBUG_LEAVE("visitExprRefPathContext -- fail");
        return;
    }

    // Set root reference
    i->setTarget(target);

    ast::IScopeChild *target_c = TaskResolveSymbolPathRef(
        m_ctxt->getDebugMgr(), 
        m_ctxt->root(),
        m_ctxt->inlineCtxt()).resolve(target);
    ast::ISymbolScope *target_s = 0;
    
    if (target_c) {
        target_s = TaskGetElemSymbolScope(
            m_ctxt->getDebugMgr(), m_ctxt->root()).resolve(target_c);
    }

    DEBUG("target_c=%p target_s=%p", target_c, target_s);

    // Check if target_c is a field or local variable with a built-in type that has methods (e.g., string)
    bool is_builtin_with_methods = false;
    ast::IDataType *target_type = 0;
    
    if (!target_s && target_c) {
        // Check if it's a field declaration
        ast::IField *field = dynamic_cast<ast::IField *>(target_c);
        if (field && field->getType()) {
            target_type = field->getType();
        }
        
        // Check if it's a procedural data declaration (local variable)
        if (!target_type) {
            ast::IProceduralStmtDataDeclaration *var_decl = 
                dynamic_cast<ast::IProceduralStmtDataDeclaration *>(target_c);
            if (var_decl && var_decl->getDatatype()) {
                target_type = var_decl->getDatatype();
            }
        }
        
        // Check if the type is a string
        if (target_type) {
            ast::IDataTypeString *string_type = dynamic_cast<ast::IDataTypeString *>(target_type);
            if (string_type) {
                is_builtin_with_methods = true;
                DEBUG("Found string variable '%s' - allowing method calls", 
                    i->getHier_id()->getElems().at(0)->getId()->getId().c_str());
            }
        }
    }

    if (!target_s && !is_builtin_with_methods && i->getHier_id()->getElems().size() > 1) {
        m_ctxt->addMarker(
            MarkerSeverityE::Error,
            i->getHier_id()->getElems().at(0)->getId()->getLocation(),
            "root ref-path element %s is not a composite scope",
            i->getHier_id()->getElems().at(0)->getId()->getId().c_str());

        DEBUG_LEAVE("visitExprRefPathContext -- fail");
        return;
    }

    // Target already points to the first elem
    i->getHier_id()->getElems().at(0)->setTarget(-1);

    for (uint32_t ii=0; ii<i->getHier_id()->getElems().size(); ii++) {
        ast::IExprMemberPathElem *elem = i->getHier_id()->getElems().at(ii).get();

        DEBUG("ii=%0d %s: subscript=%d params=%p", 
            ii, 
            elem->getId()->getId().c_str(),
            elem->getSubscript().size(), 
            elem->getParams());

        // Ensure we resolve expression references in function parameters
        if (elem->getParams()) {
            DEBUG_ENTER("Resolve parameter references");
            for (std::vector<ast::IExprUP>::const_iterator
                it=elem->getParams()->getParameters().begin();
                it!=elem->getParams()->getParameters().end(); it++) {
                (*it)->accept(m_this);
            }
            DEBUG_LEAVE("Resolve parameter references");
        }

        for (std::vector<ast::IExprUP>::const_iterator
            it=elem->getSubscript().begin();
            it!=elem->getSubscript().end(); it++) {
            (*it)->accept(m_this);
        }

//        if (!ii) {
            if (ii+1 < i->getHier_id()->getElems().size() && elem->getSubscript().size()) {
                if (elem->getSubscript().size() > 1) {
                    DEBUG_ERROR("Handle multi-dim array subscript");
                }
                target_s = TaskGetSubscriptSymbolScope(
                    m_ctxt->getDebugMgr(), m_ctxt->root()).resolve(
                        target_c
                    );
            }
            if (!ii) {
                continue;
            }
//        }

        DEBUG("Search for elem=%s target_s=%s", 
            elem->getId()->getId().c_str(),
            (target_s)?target_s->getName().c_str():"null");

        if (target_s && target_s->getOpaque()) {
            DEBUG("Note: scope is opaque ; ending hierarchical search");
            break;
        }

        // Special handling for string methods
        if (!target_s && is_builtin_with_methods && ii == 1) {
            // This is a method call on a string type - validate method name
            std::string method_name = elem->getId()->getId();
            static const std::set<std::string> valid_string_methods = {
                "size", "find", "find_last", "find_all", 
                "lower", "upper", "split", "chars"
            };
            
            if (valid_string_methods.find(method_name) != valid_string_methods.end()) {
                DEBUG("Valid string method: %s", method_name.c_str());
                // Set a sentinel value to indicate this is a built-in method
                elem->setTarget(-2); // Use -2 to distinguish from unresolved (-1)
                // Resolve parameters if present
                if (elem->getParams()) {
                    DEBUG_ENTER("Resolve string method parameters");
                    for (std::vector<ast::IExprUP>::const_iterator
                        it=elem->getParams()->getParameters().begin();
                        it!=elem->getParams()->getParameters().end(); it++) {
                        (*it)->accept(m_this);
                    }
                    DEBUG_LEAVE("Resolve string method parameters");
                }
                // String methods don't chain, so we're done
                break;
            } else {
                m_ctxt->addErrorMarker(
                    elem->getId()->getLocation(),
                    "Unknown string method '%s'", 
                    method_name.c_str());
                DEBUG("ERROR: Unknown string method %s", method_name.c_str());
                break;
            }
        }

        TaskFindPathElem::Result res = TaskFindPathElem(
            m_ctxt->getDebugMgr(), 
            m_ctxt->root()).find(
                target_s,
                elem->getId()
            );

        std::unordered_map<std::string, int32_t>::const_iterator it = 
            target_s->getSymtab().find(elem->getId()->getId());
        
        if (!res.sym) {
            m_ctxt->addErrorMarker(
                elem->getId()->getLocation(),
                "Failed to find elem %s", 
                elem->getId()->getId().c_str());

            DEBUG("ERROR: Failed to find elem %s (ii=%d)", 
                elem->getId()->getId().c_str(),
                ii);
            break;
        } else {
            DEBUG("NOTE: Found sub-element %s", elem->getId()->getId().c_str());
            elem->setTarget(res.idx);
            elem->setSuper(res.super_idx);

            // Resolve name references for parameter values
            if (elem->getParams()) {
                elem->getParams()->accept(m_this);
            }

            if (ii+1 < i->getHier_id()->getElems().size()) {
                target_c = res.sym;
                target_s = TaskGetElemSymbolScope(
                    m_ctxt->getDebugMgr(), m_ctxt->root()).resolve(
                        target_c
                    );
                if (!target_s) {
                    DEBUG_ERROR("target_s is null");
                    break;
                }

                if (elem->getSubscript().size()) {
                    if (elem->getSubscript().size() > 1) {
                        DEBUG_ERROR("Handle multi-dim array subscript");
                    }
                    target_s = TaskGetSubscriptSymbolScope(
                        m_ctxt->getDebugMgr(), m_ctxt->root()).resolve(
                            target_s
                        );
                }
                DEBUG("Next target_s: %s", target_s->getName().c_str());
            }
        }
    }

    if (target_c) {
        m_ctxt->addRef(
            i->getHier_id()->getElems().front()->getId()->getLocation().fileid,
            target_c->getLocation().fileid);
    }

    DEBUG_LEAVE("visitExprRefPathContext");
}

void TaskResolveRefs::visitActivityDecl(ast::IActivityDecl *i) {
    DEBUG_ENTER("visitActivityDecl");
    VisitorBase::visitActivityDecl(i);
    DEBUG_LEAVE("visitActivityDecl");
}

void TaskResolveRefs::visitActivitySequence(ast::IActivitySequence *i) {
    DEBUG_ENTER("visitActivitySequence");
    VisitorBase::visitActivitySequence(i);
    DEBUG_LEAVE("visitActivitySequence");
}


void TaskResolveRefs::visitExprRefPathId(ast::IExprRefPathId *i) {
    DEBUG_ENTER("visitExprRefPathId %s", i->getId()->getId().c_str());
    ast::ISymbolRefPath *target = TaskResolveRef(m_ctxt).resolve(i);
    if (!target) {
        m_ctxt->addErrorMarker(
            i->getId()->getLocation(),
            "failed to resolve ref-path %s", 
            i->getId()->getId().c_str());
    } else {
        ast::IScopeChild *target_c = m_ctxt->resolveSymbolPathRef(target);
        m_ctxt->addRef(
            i->getId()->getLocation().fileid,
            target_c->getLocation().fileid);
    }
    i->setTarget(target);
    DEBUG_LEAVE("visitExprRefPathId");
}

void TaskResolveRefs::visitExprRefPathStatic(ast::IExprRefPathStatic *i) {
    DEBUG_ENTER("visitExprRefPathStatic size=%d", i->getBase().size());
    ast::ISymbolRefPath *target = 0;
    if (i->getIs_global()) {
        DEBUG("TODO: support global-rooted references");
    } else {
        // relative root
        ast::ISymbolRefPath *target = 0;
        ast::IScopeChild *target_s = 0;
        bool in_pyref = false;
        for (std::vector<ast::ITypeIdentifierElemUP>::const_iterator
            it=i->getBase().begin();
            it!=i->getBase().end(); it++) {
            if (it==i->getBase().begin()) {
                target = TaskResolveRef(m_ctxt).resolve((*it)->getId());
                
                if (!target) {
                    addMarker(
                        MarkerSeverityE::Error,
                        (*it)->getId()->getLocation(),
                        "failed to resolve symbol %s",
                        (*it)->getId()->getId().c_str());
                    break;
                }

                if ((*it)->getParams()) {
                    DEBUG("Ref elem %d is parameterized", (it-i->getBase().begin()));

                    // Build out parameter value list
                    target = TaskSpecializeParameterizedRef(m_ctxt).specialize(
                            target, 
                            (*it)->getParams());

                    // TODO: do we need to delete target?
                }

                target_s = m_ctxt->resolveSymbolPathRef(target);

                if ((*it)->getParams()) {
                    DEBUG("Ref elem is parameterized");
                }

                if (!in_pyref) {
                    in_pyref |= TaskIsPyRef(m_ctxt->getDebugMgr(), m_ctxt->root()).check(target_s);
                    if (in_pyref) {
                        target->setPyref_idx(0);
                    } else {
                    }
                }
            } else if (!in_pyref) {
                // Need to resolve within root element ... unless we're down a Python scope
                // Visit the element to resolve internal references
                (*it)->accept(m_this);

            } else {
                DEBUG("element is inside a pyref path");
            }
        }
        i->setTarget(target);
    }

    if (target) {
        ast::IScopeChild *target_c = m_ctxt->resolveSymbolPathRef(target);
        m_ctxt->addRef(
            i->getBase().front()->getId()->getLocation().fileid,
            target_c->getLocation().fileid);
    }
    DEBUG_LEAVE("visitExprRefPathStatic");
}

void TaskResolveRefs::visitExprRefPathStaticRooted(ast::IExprRefPathStaticRooted *i) {
    DEBUG_ENTER("visitExprRefPathStaticRooted %s",
        i->getLeaf()->getElems().at(0)->getId()->getId().c_str());
    // Resolve the root
    if (i->getRoot()->getIs_global()) {
        ast::IExprId *id = i->getLeaf()->getElems().at(0)->getId();
        DEBUG("Global reference -- first find leaf %s", id->getId().c_str());
        std::unordered_map<std::string,int32_t>::const_iterator it;
        const std::unordered_map<std::string,int32_t> &symtab = 
            m_ctxt->symtab()->getRootScope()->getSymtab();
        
        if ((it=symtab.find(id->getId())) == symtab.end()) {
            DEBUG_ERROR("Failed to resolve leaf %s", id->getId().c_str());
            for (it=symtab.begin(); it!=symtab.end(); it++) {
                DEBUG("Symbol: %s", it->first.c_str());
            }
        } else {
            ast::ISymbolRefPath *ref = 
                m_ctxt->getFactory()->getAstFactory()->mkSymbolRefPath();
            ast::SymbolRefPathElem elem;
            elem.kind = ast::SymbolRefPathElemKind::ElemKind_ChildIdx;
            elem.idx = it->second;
            ref->getPath().push_back(elem);
            i->getRoot()->setTarget(ref);
        }
    } else {
        i->getRoot()->accept(m_this);

        if (!i->getRoot()->getTarget()) {
            DEBUG_LEAVE("visitExprRefPathStaticRooted -- failed root resolution");
            return;
        }

        i->getLeaf()->accept(m_this);

        if (i->getRoot()->getTarget()->getPyref_idx() != -1) {
            // The root ends in a Python-type reference
            DEBUG("Root (static) reference has a Python component");
        } else {
            DEBUG("Root (static) reference does not have a Python component");
            DEBUG("TODO: visitExprRefPathStaticRooted");
        }
    }

    DEBUG_LEAVE("visitExprRefPathStaticRooted");
}

void TaskResolveRefs::visitExtendEnum(ast::IExtendEnum *i) {
    DEBUG_ENTER("visitExtendEnum");
    DEBUG("Note: Skip during core symbol resolution");
    DEBUG_LEAVE("visitExtendEnum");
}

void TaskResolveRefs::visitExtendType(ast::IExtendType *i) {
    DEBUG_ENTER("visitExtendType");
    DEBUG("Note: Skip during core symbol resolution");
    DEBUG_LEAVE("visitExtendType");
}

void TaskResolveRefs::visitField(ast::IField *i) {
    DEBUG_ENTER("visitField %s", i->getName()->getId().c_str());
    if (i->getType()) {
        i->getType()->accept(m_this);
    }
    if (i->getInit()) {
        i->getInit()->accept(m_this);
    }
    DEBUG_LEAVE("visitField %s", i->getName()->getId().c_str());
}

void TaskResolveRefs::visitFieldCompRef(ast::IFieldCompRef *i) {
    DEBUG_ENTER("visitFieldCompRef");
    DEBUG("Note: Skip during core symbol resolution");
    DEBUG_LEAVE("visitFieldCompRef");
}

void TaskResolveRefs::visitFunctionPrototype(ast::IFunctionPrototype *i) {
    DEBUG_ENTER("visitFunctionPrototype");

    if (i->getRtype()) {
        i->getRtype()->accept(m_this);
    }

    for (std::vector<ast::IFunctionParamDeclUP>::const_iterator
        it=i->getParameters().begin();
        it!=i->getParameters().end(); it++) {
        if ((*it)->getType()) {
            (*it)->getType()->accept(m_this);
        } else {
            // TODO: likely a category type
        }
    }
    DEBUG_LEAVE("visitFunctionPrototype");
} 

void TaskResolveRefs::visitProceduralStmtRepeat(ast::IProceduralStmtRepeat *i) {
    DEBUG_ENTER("visitProceduralStmtRepeat %d", i->getSymtab().size());
    m_ctxt->symtab()->pushScope(i);
    i->getBody()->accept(m_this);
    m_ctxt->symtab()->popScope();
    DEBUG_LEAVE("visitProceduralStmtRepeat");
}

void TaskResolveRefs::visitSymbolScope(ast::ISymbolScope *i) {
    DEBUG_ENTER("visitSymbolScope %s", i->getName().c_str());
    /*
    if (i->getName() != "") {
        if (m_ctxt->symtab()->pushNamedScope(i->getName()) == -1) {
            // TODO: internal error
            fprintf(stdout, "Internal Error: no scope named %s in %s\n", 
                i->getName().c_str(),
                m_ctxt->symtab()->getScope()->getName().c_str());
        }
    } else {
        */
        m_ctxt->symtab()->pushScope(i);
//    }

    if (i->getImports()) {
        DEBUG_ENTER("  Resolve Imports");
        TaskResolveImports(m_ctxt).resolve(i);
        DEBUG_LEAVE("  Resolve Imports");
    }

    DEBUG("Have %d children", i->getChildren().size());
    DEBUG_ENTER("visit children");
    for (std::vector<ast::IScopeChildUP>::const_iterator
        it=i->getChildren().begin();
        it!=i->getChildren().end(); it++) {
        DEBUG_ENTER("visit child");
        it->get()->accept(this);
        DEBUG_LEAVE("visit child");
    }
    DEBUG_LEAVE("visit children");

    m_ctxt->symtab()->popScope();
    DEBUG_LEAVE("visitSymbolScope %s", i->getName().c_str());
}

void TaskResolveRefs::visitSymbolExtendScope(ast::ISymbolExtendScope *i) {
    DEBUG_ENTER("visitSymbolExtendScope");
    DEBUG("Note: Skipping during core symbol resolution");

/*
    m_symtab_it->pushScope(i);

    for (std::vector<ast::IScopeChild *>::const_iterator
        it=i->getChildren().begin();
        it!=i->getChildren().end(); it++) {
        (*it)->accept(this);
    }

    m_symtab_it->popScope();
 */

    DEBUG_LEAVE("visitSymbolExtendScope");
}

// void TaskResolveRefs::visitSymbolExecScope(ast::ISymbolExecScope *i) {
//     DEBUG_ENTER("visitSymbolExecScope \"%s\"", i->getName().c_str());
//     m_ctxt->symtab()->pushScope(i);

//     for (std::vector<ast::IScopeChildUP>::const_iterator
//         it=i->getChildren().begin();
//         it!=i->getChildren().end(); it++) {
//         (*it)->accept(this);
//     }

//     m_ctxt->symtab()->popScope();
//     DEBUG_LEAVE("visitSymbolExecScope \"%s\"", i->getName().c_str());
// }

void TaskResolveRefs::visitSymbolFunctionScope(ast::ISymbolFunctionScope *i) {
    DEBUG_ENTER("visitSymbolFunctionScope %s (%d %p) ", 
    i->getName().c_str(),
    i->getPrototypes().size(),
    i->getBody());

    for (std::vector<ast::IFunctionPrototype *>::const_iterator
        it=i->getPrototypes().begin();
        it!=i->getPrototypes().end(); it++) {
        (*it)->accept(m_this);
    }

//    if (i->getBody()) {
        DEBUG("Push function scope %s", i->getName().c_str());
        m_ctxt->symtab()->pushScope(i);
//        m_ctxt->symtab()->pushScope(i->getPlist());
//        DEBUG("Push function body scope");
//        m_ctxt->symtab()->pushScope(i->getBody());
        for (std::vector<ast::IScopeChildUP>::const_iterator
            it=i->getChildren().begin();
            it!=i->getChildren().end(); it++) {
            (*it)->accept(m_this);
        }

        // Resolve references in the body
        if (i->getBody()) {
            DEBUG("--> visitBody");
            i->getBody()->accept(m_this);
            DEBUG("<-- visitBody");
        }

//        m_ctxt->symtab()->popScope();
        m_ctxt->symtab()->popScope();
//    }


    DEBUG_LEAVE("visitSymbolFunctionScope %s", i->getName().c_str());
}

// void TaskResolveRefs::visitSymbolStmtScope(ast::ISymbolStmtScope *i) {
//     DEBUG_ENTER("visitSymbolStmtScope %s", i->getName().c_str());
//     m_ctxt->symtab()->pushScope(i);
//     i->getTarget()->accept(m_this);
//     m_ctxt->symtab()->popScope();
//     DEBUG_LEAVE("visitSymbolStmtScope %s", i->getName().c_str());
// }

void TaskResolveRefs::visitSymbolTypeScope(ast::ISymbolTypeScope *i) {
    ast::ITypeScope *i_ts = dynamic_cast<ast::ITypeScope *>(i->getTarget());
    DEBUG_ENTER("visitSymbolTypeScope %s (param=%s specialized=%s)", 
        i->getName().c_str(),
        (i_ts->getParams())?"true":"false",
        (i_ts->getParams() && i_ts->getParams()->getSpecialized())?"true":"false");
    if (i_ts->getParams() && !i_ts->getParams()->getSpecialized()) {
        DEBUG("Note: Skipping symbol resolution in an unspecialized templated type");
    } else {
        ast::SymbolRefPathElemKind kind = ast::SymbolRefPathElemKind::ElemKind_ChildIdx;

        if (i_ts->getParams() && i_ts->getParams()->getSpecialized()) {
            kind = ast::SymbolRefPathElemKind::ElemKind_TypeSpec;
            DEBUG("Processing specialization depth=%d", m_ctxt->specializationDepth());

            // TODO: need a way to detect that we have a superseding 
            // scope stack, so we don't redo it

            // Create a symbol-table iterator that:
            // - starts with m_root
            // - is preloaded with the scopes of the target type

            if (m_ctxt->specializationDepth() == 1) {
                DEBUG("Updating resolution stack to use local scope");
                m_ctxt->pushSymtab(TaskResolveSymbolPathRef(
                    m_ctxt->getDebugMgr(), m_ctxt->root()).mkIterator(
                        m_ctxt->getFactory()->mkAstSymbolTableIterator(m_ctxt->root()),
                        i));
            } else {
                DEBUG("Retaining existing resolution stack");
            }
            // TODO: need to resolve refs in the parameter list
            // relative to the containing type
            // Ensure parameter references are resolved
            DEBUG_ENTER("Resolve refs in parameter decl list");
            i_ts->getParams()->accept(m_this);
            DEBUG_LEAVE("Resolve refs in parameter decl list");
            if (m_ctxt->specializationDepth() == 1) {
                m_ctxt->popSymtab();
            }
        }

        // TODO: might need to defer this until after we've resolved
        // super-class
        m_ctxt->symtab()->pushScope(i, kind);

        // Resolve the super class (if any)
        if (dynamic_cast<ast::ITypeScope *>(i->getTarget())->getSuper_t()) {
            DEBUG("%s Has a super type ... resolving", i->getName().c_str());
            dynamic_cast<ast::ITypeScope *>(i->getTarget())->getSuper_t()->accept(this);
        } else {
            DEBUG("No super type");
        }

        if (i->getImports()) {
            DEBUG_ENTER("  Resolve Imports");
            TaskResolveImports(m_ctxt).resolve(i);
            DEBUG_LEAVE("  Resolve Imports");
        }

        // Check on children
        for (std::vector<ast::IScopeChildUP>::const_iterator
            it=i->getChildren().begin();
            it!=i->getChildren().end(); it++) {
            (*it)->accept(m_this);
        }

        m_ctxt->symtab()->popScope();
    }
    DEBUG_LEAVE("visitSymbolTypeScope %s", i->getName().c_str());
}

void TaskResolveRefs::visitDataTypeUserDefined(ast::IDataTypeUserDefined *i) {
    DEBUG_ENTER("visitDataTypeUserDefined");
    if (i->getType_id()->getTarget()) {
        DEBUG("Symbol already resolved");
        DEBUG_LEAVE("visitDataTypeUserDefined");
        return;
    }
    ast::ISymbolRefPath *target = TaskResolveRef(m_ctxt).resolve(i->getType_id());

    if (target) {
        DEBUG("Success");
        i->getType_id()->setTarget(target);

        ast::IScopeChild *target_c = m_ctxt->resolveSymbolPathRef(target);
        m_ctxt->addRef(
            i->getLocation().fileid,
            target_c->getLocation().fileid);
    } else {
        DEBUG("Failed");
        // char tmp[1024];
        // sprintf(tmp, "failed to find user-defined datatype");
        // IMarkerUP marker(m_factory->mkMarker(
        //     tmp,
        //     MarkerSeverityE::Error,
        //     i->getLocation()
        // ));
        // m_marker_l->marker(marker.get());
    }

    DEBUG_LEAVE("visitDataTypeUserDefined");
}


void TaskResolveRefs::visitTypeIdentifier(ast::ITypeIdentifier *i) {
    DEBUG_ENTER("visitTypeIdentifier %s", i->getElems().at(0)->getId()->getId().c_str());
    ast::ISymbolRefPath *target = TaskResolveRef(m_ctxt).resolve(i);

    if (target) {
        ast::IScopeChild *target_c = m_ctxt->resolveSymbolPathRef(target);
        m_ctxt->addRef(
            i->getElems().front()->getId()->getLocation().fileid,
            target_c->getLocation().fileid);
    }
    i->setTarget(target);
    DEBUG_LEAVE("visitTypeIdentifier");
}

void TaskResolveRefs::visitStruct(ast::IStruct *i) {
    DEBUG_ENTER("visitStruct");
    VisitorBase::visitStruct(i);
    DEBUG_LEAVE("visitStruct");
}

ast::IScopeChild *TaskResolveRefs::resolvePath(ast::ISymbolRefPath *path) {
    ast::ISymbolScope *scope = m_ctxt->root();
    ast::IScopeChild *ret = m_ctxt->root();

    for (std::vector<ast::SymbolRefPathElem>::const_iterator
        it=path->getPath().begin();
        it!=path->getPath().end(); it++) {
        ret = scope->getChildren().at(it->idx).get();

        if (it+1 != path->getPath().end()) {
            scope = dynamic_cast<ast::ISymbolScope *>(ret);
        }
    }
    
    return ret;
}

dmgr::IDebug *TaskResolveRefs::m_dbg = 0;

}
}
