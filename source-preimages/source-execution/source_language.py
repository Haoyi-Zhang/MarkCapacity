"""Hygienic CPython source realization of the owned pure arithmetic fragment.

This is a deliberately small admission grammar, not a validator for arbitrary
Python. Only exact integer Boolean arguments, literal one, addition, fresh
one-use temporaries and tuple return are admitted. No call/import/effect surface
is executed. Capacity labels come from the established arithmetic model.
"""
from __future__ import annotations

import ast
import copy

import arithmetic_language as language


def inspect_source(source: str):
    """Read actual syntax and binding before interpreting or compiling it."""
    if type(source) is not str:
        raise ValueError('source must be text')
    try:
        tree=ast.parse(source)
    except (SyntaxError,ValueError) as error:
        raise ValueError('invalid source syntax') from error
    if len(tree.body)!=1 or not isinstance(tree.body[0],ast.FunctionDef):
        raise ValueError('one ordinary function is required')
    fn=tree.body[0]
    args=fn.args
    n=len(args.args)
    if (fn.name!='carrier' or fn.decorator_list or fn.returns or getattr(fn,'type_params',())
            or args.posonlyargs or args.vararg or args.kwarg or args.kwonlyargs
            or args.defaults or args.kw_defaults
            or any(a.annotation for a in args.args)
            or [a.arg for a in args.args]!=[f'x{i}' for i in range(n)]):
        raise ValueError('fixed unannotated positional signature required')
    if not fn.body or not isinstance(fn.body[-1],ast.Return):
        raise ValueError('function must end in tuple return')
    result=fn.body[-1].value
    if not isinstance(result,ast.Tuple) or len(result.elts)!=n:
        raise ValueError('one tuple result per argument required')
    bindings={}
    for statement in fn.body[:-1]:
        if (not isinstance(statement,ast.Assign) or len(statement.targets)!=1
                or not isinstance(statement.targets[0],ast.Name)):
            raise ValueError('only simple fresh temporary assignments are admitted')
        name=statement.targets[0].id
        if name in bindings or name in {a.arg for a in args.args} or name=='carrier':
            raise ValueError('temporary binding must be fresh and unique')
        bindings[name]=statement.value
    components=[]
    expression_nodes=[]
    used=set()
    for i,node in enumerate(result.elts):
        named=isinstance(node,ast.Name)
        if named:
            if node.id not in bindings or node.id in used:
                raise ValueError('each temporary must be returned exactly once')
            used.add(node.id)
            expression=bindings[node.id]
        else:
            expression=node
        if not isinstance(expression,ast.BinOp) or not isinstance(expression.op,ast.Add):
            raise ValueError('component must be a pure addition')
        def operand(value):
            if isinstance(value,ast.Name) and value.id==f'x{i}' and isinstance(value.ctx,ast.Load):
                return language.Var(f'x{i}')
            if isinstance(value,ast.Constant) and type(value.value) is int and value.value==1:
                return language.Lit(1)
            raise ValueError('component needs its own argument and integer literal one')
        model_expression=language.Add(operand(expression.left),operand(expression.right))
        component=(language.Let('t',model_expression,language.Return(language.Var('t')))
                   if named else language.Return(model_expression))
        components.append(component)
        expression_nodes.append(expression)
    if used!=set(bindings):
        raise ValueError('unreturned temporary is outside the fragment')
    model=language.Procedure(tuple(components))
    language.shape(model)
    return model,tree,expression_nodes


def parse_source(source: str) -> language.Procedure:
    return inspect_source(source)[0]


def render(procedure: language.Procedure) -> str:
    """Allocate distinct function-local names for model component-local scopes."""
    orders,names=language.shape(procedure)
    statements=[]
    values=[]
    for i,(order,named) in enumerate(zip(orders,names,strict=True)):
        expression=f'1 + x{i}' if order else f'x{i} + 1'
        if named:
            statements.append(f'    v{i} = {expression}')
            values.append(f'v{i}')
        else:
            values.append(expression)
    result='('+', '.join(values)+(',' if len(values)==1 else '')+')'
    return 'def carrier('+', '.join(f'x{i}' for i in range(len(orders)))+'):\n'+\
           '\n'.join([*statements,'    return '+result])+'\n'


def compile_source(source: str):
    """Execute only the admitted owned grammar in an isolated empty namespace."""
    model,tree,_=inspect_source(source)
    n=len(model.components)
    namespace={'__builtins__':{}}
    exec(compile(tree,'<owned-markcapacity-fragment>','exec'),namespace)
    function=namespace['carrier']
    def run(inputs):
        if type(inputs) is not tuple or len(inputs)!=n or any(type(x) is not int or x not in (0,1) for x in inputs):
            raise ValueError('exact integer Boolean tuple required')
        return function(*inputs)
    return run


def commute(source: str,site: int) -> str:
    """Swap actual AST operands at one admitted source site."""
    model,tree,nodes=inspect_source(source)
    if type(site) is not int or not 0<=site<len(model.components):
        raise ValueError('site outside the source fragment')
    node=nodes[site]
    node.left,node.right=node.right,node.left
    changed=ast.unparse(tree)+'\n'
    parse_source(changed)
    return changed


def rename_form(source: str,site: int) -> str:
    """One actual let-introduction/elimination, followed by alpha-canonical print."""
    model,tree,_=inspect_source(source)
    if type(site) is not int or not 0<=site<len(model.components):
        raise ValueError('site outside the source fragment')
    fn=tree.body[0]
    value=fn.body[-1].value.elts[site]
    if isinstance(value,ast.Name):
        assignment=next(s for s in fn.body[:-1] if s.targets[0].id==value.id)
        fn.body[-1].value.elts[site]=copy.deepcopy(assignment.value)
        fn.body.remove(assignment)
    else:
        names={a.arg for a in fn.args.args}|{s.targets[0].id for s in fn.body[:-1]}
        name=f'v{site}'
        while name in names:
            name+='_'  # Freshness is semantic, not a formatting preference.
        fn.body.insert(-1,ast.Assign(targets=[ast.Name(id=name,ctx=ast.Store())],value=copy.deepcopy(value)))
        fn.body[-1].value.elts[site]=ast.Name(id=name,ctx=ast.Load())
    ast.fix_missing_locations(tree)
    return render(parse_source(ast.unparse(tree)))


def source_reachable(source: str) -> frozenset[str]:
    """Independent AST rewrite path; budget is carried across naming steps."""
    source=render(parse_source(source))
    n=len(parse_source(source).components)
    seen={(source,0)}
    pending=[(source,0)]
    while pending:
        current,spent=pending.pop()
        for i in range(n):
            for changed,cost in ((rename_form(current,i),0),(commute(current,i),1)):
                changed=render(parse_source(changed))
                state=(changed,spent+cost)
                if state[1]<=1 and state not in seen:
                    seen.add(state)
                    pending.append(state)
    return frozenset(s for s,_ in seen)


def encode(source: str,message: int,sites=()) -> str:
    model=parse_source(source)
    return render(language.embed(model,message,sites))


def decode(source: str,sites=()) -> int:
    return language.syndrome(parse_source(source),sites)


def attack_sources(source: str,sites=()) -> tuple[str,...]:
    orders,names=language.shape(parse_source(source))
    sites=language.normalized_sites(len(orders),sites)
    return tuple(rename_form(source,i) for i,named in enumerate(names) if named)+\
           tuple(commute(source,i) for i in sorted(sites) if orders[i])
