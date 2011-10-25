from pyparsing import *
#from batchlang import *
from batchgen import *
from batchstats import *
from batchoptimizer import *
import string,sys

objStack = []

def createNode(s, loc, toks):
    print('createNode => ', toks)
    return BinaryNode(toks[0])

# convert 'attr < value' to a binary tree based on 'or' and 'and'
def parseNumConditional(s, loc, toks):
    print("print: %s" % toks)
    return BinaryNode(toks[0])

def markPublic(s, loc, toks):
    print("public: %s" % toks)
    return toks

def markSecret(s, loc, toks):
    print("secret: %s" % toks)
    return toks
        
def pushFirst( s, loc, toks ):
    if debug >= levels.some:
       print("Pushing first =>", toks[0])
    objStack.append( toks[0] )

def createTree(op, node1, node2):
    if(op == "^"):
        node = BinaryNode(ops.EXP)
    elif(op == "*"):
        node = BinaryNode(ops.MUL)
    elif(op == "+"):
        node = BinaryNode(ops.ADD)
    elif(op == ":="):
        node = BinaryNode(ops.EQ)
    elif(op == "=="):
        node = BinaryNode(ops.EQ_TST)
    elif(op == "e("):
        node = BinaryNode(ops.PAIR)
    elif(op == "H("):
        node = BinaryNode(ops.HASH)
    elif(op == "prod{"):
        node = BinaryNode(ops.PROD)
    elif(op == "on"):
        # can only be used in conjunction w/ PROD (e.g. PROD must precede it)        
        node = BinaryNode(ops.ON)
    elif(op == "|"):
        node = BinaryNode(ops.CONCAT)
    # elif e( ... )
    else:    
        return None
    node.addSubNode(node1, node2)
    return node

class BatchParser:
    def __init__(self, verbose=False):
        self.finalPol = self.getBNF()
        self.verbose = verbose

    def getBNF(self):
        # supported operators => (OR, AND, <, prod{
        #OperatorOR = Literal("OR") | Literal("or").setParseAction(upcaseTokens)
        #OperatorAND = Literal("AND") | Literal("and").setParseAction(upcaseTokens)
        lpar = Literal("(").suppress() | Literal("{").suppress()
        rpar = Literal(")").suppress() | Literal("}").suppress()
        rcurly = Literal("}").suppress()

        MulOp = Literal("*")
        Concat = Literal("|")
        ExpOp = Literal("^")
        AddOp = Literal("+")
        Equality = Literal("==") # | Word("<>", max=1)
        BinOp = ExpOp | MulOp | AddOp | Concat | Equality
        Assignment =  Literal(":=")
        Pairing = Literal('e(') # Pairing token
        Hash = Literal('H(')
        Prod = Literal("prod{") # dot product token
        ProdOf = Literal("on")
        # captures order of parsing token operators
        Token = Equality | ExpOp | MulOp | AddOp | ProdOf | Concat | Assignment
        Operator = Token 
        #Operator = OperatorAND | OperatorOR | Token

        # describes an individual leaf node
        leafNode = Word(alphanums + '_').setParseAction( createNode )
        expr = Forward()
        term = Forward()
        factor = Forward()
        atom = (Hash + expr + ',' + expr + rpar).setParseAction( pushFirst ) | \
               (Pairing + expr + ',' + expr + rpar).setParseAction( pushFirst ) | \
               (Prod + expr + ',' + expr + rcurly).setParseAction( pushFirst ) | \
               lpar + expr + rpar | (leafNode).setParseAction( pushFirst )

        # Represents the order of operations (^, *, |, ==)
        # Place more value on atom [ ^ factor}, so gets pushed on the stack before atom [ = factor], right?
        # In other words, adds order of precedence to how we parse the string. This means we are parsing from right
        # to left. a^b has precedence over b = c essentially
        #factor << atom + ZeroOrMore( ( ExpOp + factor ).setParseAction( pushFirst ) )
        factor << atom + ZeroOrMore( ( BinOp + factor ).setParseAction( pushFirst ) )
        
        term = atom + ZeroOrMore((Operator + factor).setParseAction( pushFirst ))
        # define placeholder set earlier with a 'term' + Operator + another term, where there can be
        # more than zero or more of the latter. Once we find a term, we first push that into
        # the stack, then if ther's an operand + term, then we first push the term, then the Operator.
        # so on and so forth (follows post fix notation).
        expr << term + ZeroOrMore((Operator + term).setParseAction( pushFirst ))
        # final bnf object
        finalPol = expr#.setParseAction( debug )
        return finalPol
    
    # method for evaluating stack assumes operators have two operands and pops them accordingly
    def evalStack(self, stack):
        op = stack.pop()
        if debug >= levels.some:
            print("op: %s" % op)
        if op in ["+", "*", "^", ":=", "==", "e(", "prod{", "on", "|"]: # == "AND" or op == "OR" or op == "^" or op == "=":
            op2 = self.evalStack(stack)
            op1 = self.evalStack(stack)
            return createTree(op, op1, op2)
        elif op in ["H("]:
            op2 = self.evalStack(stack)
            op1 = self.evalStack(stack)
            return createTree(op, op1, op2)
        else:
            # Node value
            return op
    
    # main loop for parser. 1) declare new stack, then parse the string (using defined BNF) to extract all
    # the tokens from the string (not used for anything). 3) evaluate the stack which is in a post
    # fix format so that we can pop an OR, AND, ^ or = nodes then pull 2 subsequent variables off the stack. Then,
    # recursively evaluate those variables whether they are internal nodes or leaf nodes, etc.
    def parse(self, line):
        # use lineCtr to track line of code.
        if len(line) == 0 or line[0] == '#': 
#            print("comments or empty strings will be ignored.")
            return None 
        global objStack
        del objStack[:]
        tokens = self.finalPol.parseString(line)
        if debug >= levels.some:
           print("stack =>", objStack)
        return self.evalStack(objStack)
   
    # experimental - type checking 
#    def type_check(self, node):
#        if node.type == node.EXP:
#            print("public =>", node.getLeft(), "in pk?")
#            print("secret =>", node.getRight(), "in sk?")
            
#        elif node.type == node.EQ:
#            print("public =>", node.getLeft(), "in pk?")
#            self.type_check(node.getRight())
#        elif node.type == node.AND:
#            self.type_check(node.getLeft())
#            self.type_check(node.getRight())
#        else:
#            return None
#        return None
def parseFile(filename):
    fd = open(filename, 'r')
    ast_tree = []
    parser = BatchParser()
    code = fd.readlines(); i = 1
    for line in code:
        line = line.strip('\n')
        if len(line) == 0 or line[0] == '#':
            if debug == levels.all: print(line)
            continue
        ast_node = parser.parse(line)
        print(i, ":", ast_node)
        ast_tree.append(ast_node)
        # ast_tree[i] = ast_node # store for later processing        
        i += 1
    fd.close()
    return ast_tree

# keywords
START_TOKEN, END_TOKEN = 'BEGIN', 'END'
TYPE, CONST, PRECOMP, OTHER = 'types', 'constant', 'precompute', 'other'

def clean(arr):
    return [i.strip() for i in arr]

def handle(lines, target):
    parser = BatchParser()
    if type(lines) != list:
        return parser.parse(lines)

    # check that right hand side is a node for all
#    if target == PRECOMP:
#        _ast = {}
#        for line in lines:
#            ast_node = parser.parse(line)
#                _ast.append(ast_node)
#        print("Precomputation =>")
#        return _ast
    if target == CONST:
        # parse differently 'a, b, etc.\n'
        _ast = []
        for line in lines:
            l = line.split(',')
            _ast = [i.strip() for i in l]
        print(target, " =>", _ast)
        return _ast
    elif target in [TYPE, PRECOMP]:
        _ast = {}
        for line in lines:
            ast_node = parser.parse(line)
            # make sure it's an assignment node
            # otherwise, ignore the node
            if ast_node.type == ops.EQ:
                left = str(ast_node.left)
                right = str(ast_node.right)
                _ast[ left ] = right
        print(target, " =>", _ast)
        return _ast
    return None

debugs = levels.all

def parseFile2(filename):
    fd = open(filename, 'r')
    ast = {TYPE: None, CONST: None, PRECOMP: None, OTHER: [] }
    
    # parser = BatchParser()
    code = fd.readlines(); i = 1
    inStruct = (False, None)
    queue = []
    for line in code:
        if line.find('::') != -1: # parse differently
            token = clean(line.split('::'))
            if token[0] == START_TOKEN and (token[1] in [TYPE, CONST, PRECOMP]):
                inStruct = (True, token[1])
                if debugs == levels.all: print("Got a section!!!")
                continue
            elif inStruct[0]:
                # continue until we reach an end token, then
                # test if end token matches the start token, if so can handle queue 
                key = token[1]
                if token[0] == END_TOKEN and inStruct[1] == key:
                    ast[ key ] = handle(queue, key)
                    if debugs == levels.all:
                        print("section =>", key)
                        # print("queue =>", queue)
                        # print("result =>", ast[key])
                    # check for global syntax error and exit
                    queue = [] # tmp remove everything
                    inStruct = (False, None)  
            else:
                print("Syntax Error while parsing section: ", line)

        else: # if not, keep going and assume that we can safely add lines to queue
            if inStruct[0]:
                queue.append(line)
            elif len(line.strip()) == 0 or line[0] == '#':
                print(line)
                continue
            else:
                if debugs == levels.all: 
                    print("Not in a type enclosure: ", line)
                result = handle(line, None)
                print("result =>", result)
                print("type =>", type(result))
                ast[ OTHER ].append(result)                
                
    fd.close()
    return ast

# Takes the tree and iterates through each line 
# and verifies X # of rules. This serves to notify
# the user on any errors that might have been made in
# specifying the batch inputs.
def astSyntaxChecker(astTree):
    pass

# Perform some type checking here?
# rules: find constants, verify, variable definitions
def astParser(astList):
    constants = []
    verify_eq = None
    variables = {}
    
    for i in astList:
        s = str(i.left)
        if s == 'constant':
            constants.append(str(i.right))
        elif s == 'verify':
            verify_eq = i
        else:
            variables[s] = str(i.right)

    return (constants, verify_eq, variables)

class ASTIterator:
    def __init__(self, _node, _type):
        self.cur_node = _node
        self.of_type = _type
    
    def __iter__(self):
        # if we've found a match
        if self.cur_node.type == _type:
            return self.cur_node
        else:
            self.cur_node = self.cur_node.right
    
    def next(self):
        if self.cur_node:
            raise StopIteration
        else:
            self.cur_node = _node.right

# decorator for selecting which operation to call on 
# each node visit...
class dispatch(object):
    def __init__(self, target=None):
#        print("initialized dispatcher...")
        self.target = target
        self.default = 'visit'        
        #self.meths = {}; 
        self.hit = 0
    
    def __call__(self, visitor, *args):
        def wrapped_func(*args):
            try:
                name = str(args[0].type)
                #print("dispatch for => visit_", name.lower())
                func_name = 'visit_' + name.lower()
                if hasattr(visitor, 'cache') and visitor.cache.get(func_name) == None:
                    meth = getattr(visitor, func_name, self.default)
                    if meth == self.default:
                        meth = getattr(visitor, self.default)
                    visitor.cache[func_name] = meth # cache for next call
                    meth(*args)
                else:
                    # call cached function
                    self.hit += 1
                    # print("hitting cache: ", self.hit) 
                    visitor.cache[func_name](*args)
            except Exception as e:
                print(e)

        return wrapped_func(*args)

class ASTVisitor(object):
    def __init__(self, visitor):    
        self.visitor = visitor
        if not hasattr(self.visitor, 'visit'):
            raise Exception("No generic visit method defined in AST operation class")
        if not hasattr(self.visitor, 'cache'):
            self.visitor.cache = {} # for caching funcs
        # pointers to other parts of the tree
        # allows for keeping track of where we are in
        # AST.

    @dispatch
    def visit(self, visitor, node, info):
        """Generic visit function or sub nodes"""
        return
        
    def preorder(self, root_node, parent_node=None, sib_node=None):
        if root_node == None: return None
        # if parent_node == None: parent_node = root_node
        info = { 'parent': parent_node, 'sibling': sib_node }
        self.visit(self.visitor, root_node, info) 
        self.preorder(root_node.left, root_node, root_node.right)
        self.preorder(root_node.right, root_node, root_node.left)
    
    def postorder(self, root_node, parent_node=None, sib_node=None):
        if root_node == None: return None
        # if parent_node == None: parent_node = root_node
        info = { 'parent': parent_node, 'sibling': sib_node }
        self.postorder(root_node.left, root_node, root_node.right)
        self.postorder(root_node.right, root_node, root_node.left)
        self.visit(self.visitor, root_node, info)
    
    def inorder(self, root_node, parent_node=None, sib_node=None):
        if root_node == None: return None
        # if parent_node == None: parent_node = root_node        
        info = { 'parent': parent_node, 'sibling': sib_node }
        self.inorder(root_node.left, root_node, root_node.right)
        self.visit(self.visitor, root_node, info)
        self.inorder(root_node.right, root_node, root_node.left)


def addAsChildNodeToParent(data, target_node):
    if data['parent'].right == data['sibling']:
        data['parent'].left = target_node
    else:
        data['parent'].right = target_node              


# note: 'j' is a reserved index attribute for nodes in our Signature Description Language.
class ASTAddIndex:
    def __init__(self, constants, variables):
        self.consts = constants
        self.vars   = variables 

    def visit(self, node, data):
        pass
        
    def visit_attr(self, node, data):
        if data['parent'].type in [ops.PROD, ops.EQ]:
            return
        if not self.isConstant(node):
            node.setAttrIndex('i') # add index to each attr that isn't constant
    
    def isConstant(self, node):        
        for n in self.consts:
            if n == node.getAttribute(): return True
        return False
        
class CombineVerifyEq:
    def __init__(self, constants, variables):
        self.consts = constants
        self.vars = variables
    
    def visit(self, node, data):
        pass
    
    def visit_eq_tst(self, node, data):
        # distribute prod to left and right side
        if node.left.type != ops.EQ:
            prodL = self.newProdNode()
            prodL.right = node.left
            node.left = prodL
        
        if node.right.type != ops.EQ:
            prodR = self.newProdNode()
            prodR.right = node.right
            node.right = prodR
                    
    def visit_attr(self, node, data):
        if data['parent'].type in [ops.PROD, ops.EQ]:
            return
        if not self.isConstant(node):
            node.setAttrIndex('j') # add index to each attr that isn't constant
    
    def newProdNode(self):
        p = BatchParser()
        new_node = p.parse("prod{j:=1, N} on x")
        return new_node

    def isConstant(self, node):
        if self.consts:        
            for n in self.consts:
                if n == node.getAttribute(): return True            
            #if n.getAttribute() == node.getAttribute(): return True
        return False

# Focuses on simplifying dot products of the form
# prod{} on (x * y)
class SimplifyDotProducts:
    def __init__(self):
        pass
    
    def visit(self, node, data):
        pass
    
    def visit_on(self, node, data):
        if Type(data['parent']) == ops.PAIR:
            return
        #print("test: right node of prod =>", node.right, ": type =>", node.right.type)
        #print("parent type =>", Type(data['parent']))
        _type = node.right.type
        if _type == ops.MUL:
            # must distribute prod to both children of mul
            mul_node = node.right
            # in case we're dealing with prod{} on attr1 * attr2 
            # no need to simply further, so we can simply return
            if mul_node.left.type == ops.ATTR and mul_node.right.type == ops.ATTR:
                return

            node.right = None
            prod_node2 = BinaryNode.copy(node)
            
            # add prod nodes to children of mul_node
            prod_node2.right = mul_node.right
            mul_node.right = prod_node2
            
            node.right = mul_node.left
            mul_node.left = node
            
            # move mul_node one level up to replace the "on" node.
            addAsChildNodeToParent(data, mul_node)
        

# Adds an exponent to a \delta to every pairing node
# TODO: when you discover that a node already has an EXP node, then change right node
# to a MUL between that value and delta. e.g. prod{} on x^b => prod{} on x^(b * delta).
class SmallExponent:
    def __init__(self, constants, variables):
        self.consts = constants
        self.vars   = variables
    
    def visit(self, node, data):
        pass

    # find  'prod{i} on x' transform into ==> 'prod{i} on (x)^delta_i'
    def visit_on(self, node, data):
        prod = node.left
        # Restrict to only product nodes that we've introduced for 
        # iterating over the N signatures
        if str(prod.right) != 'N':
            return
        
        if node.right.type == ops.EXP:
            exp = node.right
            mul = BinaryNode(ops.MUL)
            mul.right = BinaryNode("delta_j")
            mul.left = exp.right
            exp.right = mul
        else:
            new_node = self.newExpNode()
            new_node.left = node.right
            new_node.right = BinaryNode("delta_j")
            node.right = new_node
#            new_node.right.setAttrIndex('j') # make more programmatic
    
    def newExpNode(self):
#        exp = BinaryNode(ops.EXP)
        p = BatchParser()
        _node = p.parse("a ^ b_i")
        return _node

class Technique2:
    def __init__(self, constants, variables, group='G1'):
        self.consts = constants
        self.vars   = variables
        print("Rule 2: Move the exponent(s) into the pairing")
        self.group = group # can orogrammatically set which group we move exponent into
        # TODO: pre-processing to determine context of how to apply technique 2
        # TODO: in cases of chp.bv, where you have multiple exponents outside a pairing, move them all into the e().
    
    def visit(self, node, data):
        pass

    # find: 'e(g, h)^d_i' transform into ==> 'e(g^d_i, h)' iff g or h is constant
    # move exponent towards the non-constant attribute
    def visit_exp(self, node, data):
        # print("left node =>", node.left.type,"target right node =>", node.right)
        if(node.left.type == ops.PAIR):   # and (node.right.attr_index == 'i'): # (node.right.getAttribute() == 'delta'):
            pair_node = node.left
            addAsChildNodeToParent(data, pair_node) # move pair node one level up
                                  # make cur node the left child of pair node
            # G1 : pair.left, G2 : pair.right
            self.isConstInSubtree(pair_node.left)
            if not self.const_result:
                node.left = pair_node.left
                pair_node.left = node
            
            self.isConstInSubtree(pair_node.right)
            if not self.const_result:
                node.left = pair_node.right
                pair_node.right = node 
        # blindly move the right node of prod{} on x^delta regardless    
        elif(node.left.type == ops.ON):
            # (prod{} on x) ^ y => prod{} on x^y
            # check whether prod right
            prod_node = node.left
            addAsChildNodeToParent(data, prod_node)
            #print("prod_node right =>", prod_node.right.type)
            # look into x: does x contain a PAIR node?
            pair_node = searchNode(prod_node.right, ops.PAIR)
            # if yes: 
            if pair_node:
                # move exp inside the pair node
                # check whether left side is constant
                if not self.isConstInSubtreeT(pair_node.left):
                    #print(" pair right type =>", pair_node.right.type)
                    if Type(pair_node.right) == ops.MUL:
                        _subnodes = []
                        getListNodes(pair_node.right, ops.NONE, _subnodes)
                        if len(_subnodes) > 2: # candidate for expanding
                            muls = [ BinaryNode(ops.MUL) for i in range(len(_subnodes)-1) ]
                            for i in range(len(muls)):
                                muls[i].left = self.createExp(_subnodes[i], BinaryNode.copy(node.right))
                                if i < len(muls)-1:
                                    muls[i].right = muls[i+1]
                                else:
                                    muls[i].right = self.createExp(_subnodes[i+1], BinaryNode.copy(node.right))
                            #print("root =>", muls[0])
                            pair_node.right = muls[0]
                        else:
                            self.setNodeAs(pair_node, 'right', node, 'left')

                    elif Type(pair_node.right) == ops.ATTR:
                        self.setNodeAs(pair_node, 'right', node, 'left')

                # check whether right side is constant
                elif not self.isConstInSubtreeT(pair_node.right):
                    # check the type of pair_node : 
                    if Type(pair_node.left) == ops.MUL:
                        pass
                    elif Type(pair_node.left) == ops.ATTR:
                        self.setNodeAs(pair_node, 'left', node, 'left')

            else:
            #    blindly make the exp node the right child of whatever node
                self.setNodeAs(prod_node, 'right', node, 'left')

        elif(node.left.type == ops.MUL):
            print("Consider: node.left.type =>", node.left.type)
            mul_node = node.left
            
            
            pass
        else:
            pass

    def createExp(self, left, right):
        if left.type == ops.EXP: # left => a^b , then => a^(b * c)
            mul = BinaryNode(ops.MUL)
            mul.left = left.right
            mul.right = right
            exp = BinaryNode(ops.EXP)
            exp.left = left.left
            exp.right = mul
        elif left.type == ops.ATTR: # left: attr ^ right
            exp = BinaryNode(ops.EXP)
            exp.left = left
            exp.right = right
        return exp

    def getNodes(self, tree, parent_type, _list):
        if tree == None: return None
        elif parent_type == ops.MUL:
            if tree.type == ops.ATTR: _list.append(tree)
            elif tree.type == ops.EXP: _list.append(tree)
            elif tree.type == ops.HASH: _list.append(tree)
        
        if tree.left: self.getNodes(tree.left, tree.type, _list)
        if tree.right: self.getNodes(tree.right, tree.type, _list)
        return
    
    def setNodeAs(self, orig_node, attr_str, target_node, target_attr_str='left'):
        if attr_str == 'right':  tmp_node = orig_node.right; orig_node.right = target_node
        elif attr_str == 'left': tmp_node = orig_node.left; orig_node.left = target_node
        else: return None
        if target_attr_str == 'left': target_node.left = tmp_node
        elif target_attr_str == 'right': target_node.right = tmp_node
        else: return None
        return True
        
    def isConstInSubtree(self, node): # check whether left or right node is constant  
        if not node: return
        if node.type == ops.ATTR:
            self.const_result = self.isConstant(node)
            return
        self.isConstInSubtree(node.left)
        self.isConstInSubtree(node.right)

    def isConstInSubtreeT(self, node): # check whether left or right node is constant  
        if node == None: return None
        if node.type == ops.ATTR:
            return self.isConstant(node)
        result = self.isConstInSubtree(node.left)
        if result: return result
        result = self.isConstInSubtree(node.right)
        return result

    def isConstant(self, node):        
        for n in self.consts:
            if n == node.getAttribute(): return True
        return False

class Technique3:
    def __init__(self, constants, variables, group='G1'):
        self.consts = constants
        self.vars   = variables
        self.group  = group
        self.rule   = "Rule 3: "
        #print("Rule 3: When two pairings with common 1st or 2nd element appear, then can be combined. n pairs to 1.")
    
    def visit(self, node, data):
        pass
    
    # rare case: split a \single\ pairing into two or more pairings to allow for application of 
    # other techniques. pair(a, b * c * d?) => p(a, b) * p(a, c) * p(a, d)
    # pair with a child node with more than two mult's?
    def visit_pair(self, node, data):
        left = node.left
        right = node.right
        if left.type == ops.MUL:
            pass
        elif right.type == ops.MUL:
            pass
#            _nodes = []
#            self.getNodes(right, ops.NONE, _nodes)
#            if len(_nodes) > 2: # candidate for expanding
#                muls = [ BinaryNode(ops.MUL) for i in range(len(_nodes)-1) ]
#                for i in range(len(muls)):
#                    muls[i].left = self.createPair(left, _nodes[i])
#                    if i < len(muls)-1:
#                        muls[i].right = muls[i+1]
#                    else:
#                        muls[i].right = self.createPair(left, _nodes[i+1])
                    
#                mul = BinaryNode(ops.MUL)
#                mulrt = BinaryNode(ops.MUL)
#                i = 0
#                mulrt.left = self.createPair(left , _nodes[i])
#                mulrt.right = mul
#                i += 1
#                mul.left = self.createPair(left , _nodes[i])
#                i += 1
#                mul.right = self.createPair(left, _nodes[i])

#                print("mul root =>", muls[0])
#                addAsChildNodeToParent(data, muls[0])
        else:
            return None

    # transform prod{} on pair(x,y) => pair( prod{} on x, y) OR pair(x, prod{} on y)
    # n pairings to 1
    def visit_on(self, node, data):
        if Type(node.right) == ops.PAIR:
            pair_node = node.right
            
            l = []; r = [];
            self.getMulTokens(pair_node.left, ops.NONE, [ops.EXP, ops.HASH], l)
            self.getMulTokens(pair_node.right, ops.NONE, [ops.EXP, ops.HASH], r)
            if len(l) > 2: 
                print("T3: Need to code this case!")
                pass
            elif len(r) > 2:
            # special case: check whether we could apply the reverse split here, if there are multiple elements in             
                left = pair_node.left
                muls = [ BinaryNode(ops.MUL) for i in range(len(r)-1) ]
                for i in range(len(muls)):
                    muls[i].left = self.createPair(left, r[i])
                    if i < len(muls)-1:
                        muls[i].right = muls[i+1]
                    else:
                        muls[i].right = self.createPair(left, r[i+1])
                #print("root =>", muls[0])
                node.right = muls[0]
                self.rule += "split one pairing into two or three."
                #addAsChildNodeToParent(data, muls[0])
            else:        
                addAsChildNodeToParent(data, pair_node) # move pair one level up            
                if not self.isConstInSubtreeT(pair_node.left): # if F, then can apply prod node to left child of pair node              
                    node.right = pair_node.left
                    pair_node.left = node # pair points to 'on' node
                    self.rule += "common 1st (left) node appears, so can reduce n pairings to 1."
                elif not self.isConstInSubtreeT(pair_node.right):
                    node.right = pair_node.right
                    pair_node.right = node
                    self.rule += "common 2nd (right) node appears, so can reduce n pairings to 1."

    
    def isConstInSubtree(self, node): # check whether left or right node is constant  
        if not node: return
        if node.type == ops.ATTR:
            # set appropriate field when we've found an attribute we can check
            self.const_result = self.isConstant(node)
            return
        self.isConstInSubtree(node.left)
        self.isConstInSubtree(node.right)

    def isConstInSubtreeT(self, node): # check whether left or right node is constant  
        if node == None: return None
        if node.type == ops.ATTR:
            return self.isConstant(node)
        result = self.isConstInSubtree(node.left)
        if result: return result
        result = self.isConstInSubtree(node.right)
        return result

    def isConstant(self, node): 
        for n in self.consts:
            if n == node.getAttribute(): return True
        return False
    
    def getMulTokens(self, subtree, parent_type, target_type, _list):
        if subtree == None: return None
        elif parent_type == ops.MUL:
            if subtree.type in target_type: _list.append(subtree)
        if subtree.left: self.getMulTokens(subtree.left, subtree.type, target_type, _list)
        if subtree.right: self.getMulTokens(subtree.right, subtree.type, target_type, _list)
        return
    
    def getNodes(self, tree, parent_type, _list):
        if tree == None: return None
        elif parent_type == ops.MUL:
            if tree.type == ops.ATTR: _list.append(tree)
            elif tree.type == ops.EXP: _list.append(tree)
            elif tree.type == ops.HASH: _list.append(tree)
        
        if tree.left: self.getNodes(tree.left, tree.type, _list)
        if tree.right: self.getNodes(tree.right, tree.type, _list)
        return
    
    def createPair(self, left, right):
        pair = BinaryNode(ops.PAIR)
        pair.left = left
        pair.right = right
        return pair
        
class Technique4:
    def __init__(self, constants, variables, meta):
        print("Metadata =>", meta)
        self.consts = constants
        self.vars   = variables
        self.meta = meta
    
    def visit(self, node, data):
        pass
    
    def visit_on(self, node, data):
        prod = node.left
        my_val = str(prod.right)
        # check right subnode for another prod node
        node2 = self.searchProd(node.right)
        if node2 != None:
            # can apply technique 4 optimization
            prod2 = node2.left
            # N > x then we need to switch x with N
            if int(self.meta[str(prod.right)]) > int(self.meta[str(prod2.right)]):
                # switch nodes between prod nodes of x (constant) and N
                node.left = prod2
                node2.left = prod
    
    def searchProd(self, node):
        if node == None: return None
        elif node.type == ops.ON:
            return node
        else:
            result = self.searchProd(node.left)
            if result: return result            
            result = self.searchProd(node.right)
        return result

def print_results(data):
    line = "------------------------------------------------------------------------\n"
    head = " Keys\t|\tZR\t|\tG1\t|\tG2\t|\tGT\t|\n"
    msmt = line + head + line
    for k in data.keys():
        if k in ['mul', 'exp', 'hash']:
            msmt += k + "\t|"
            for i in ['ZR', 'G1', 'G2', 'GT']:
                msmt += "\t" + str(data[k][i]) + "\t|"
            msmt += "\n" + line
    for k in data.keys():
        if k in ['pair', 'prng']:
            msmt += k + " => " + str(data[k]) + "  \n"
            msmt += line            
    print(msmt)
    return

def calculate_times(opcount, curve, N):
    result = {}
    total_time = 0.0
    for i in opcount.keys():
        if i == 'pair':
            result[i] = opcount[i] * curve[i]
            total_time += result[i]
        else: # probably another dictionary
            result[i] = {}
            for j in opcount[i].keys():
                result[i][j] = opcount[i][j] * curve[i][j]
                total_time += result[i][j]
    print("Measurements are recorded in milliseconds.")
    print_results(result)
    print("Total Verification Time =>", total_time)
    print("Per Signature =>", total_time / N)
    print()
    return result

if __name__ == "__main__":
    print(sys.argv[1:])
    if sys.argv[1] == '-t':
        debug = levels.all
        statement = sys.argv[2]
        parser = BatchParser()
        final = parser.parse(statement)
        print("Final statement:  '%s'" % final)
        exit(0)
    elif sys.argv[1] == '-p':
        print_results(None)
        exit(0)
    #elif sys.argv[1] == '-n':
    
    # main for batch input parser    
    file = sys.argv[1]
    ast_struct = parseFile2(file)
    const, types = ast_struct[ CONST ], ast_struct[ TYPE ]
    precompute = ast_struct[ PRECOMP ]
    verify, N = None, None
    metadata = {}
    for n in ast_struct[ OTHER ]:
        if str(n.left) == 'verify':
            verify = n
        elif str(n.left) == 'N':
            N = int(str(n.right))
            metadata['N'] = str(n.right)
        else:
            metadata[ str(n.left) ] = str(n.right)

    print("Constants =>", const)
    vars = types
    vars['N'] = N
    print("Variables =>", vars)

    print("\nVERIFY EQUATION =>", verify, "\n")
    verify2 = BinaryNode.copy(verify)
    ASTVisitor(CombineVerifyEq(const, vars)).preorder(verify2.right)
    ASTVisitor(SimplifyDotProducts()).preorder(verify2.right)

    print("\nStage A: Combined Equation =>", verify2, "\n")
    ASTVisitor(SmallExponent(const, vars)).preorder(verify2.right)
    print("\nStage B: Small Exp Test =>", verify2, "\n")
    ASTVisitor(Technique2(const, vars)).preorder(verify2.right)
    #ASTVisitor(Technique2(const, vars)).preorder(verify2.right)    
    print("\nApply tech 2 =>", verify2, "\n")
    T3 = Technique3(const, vars)
    ASTVisitor(T3).preorder(verify2.right)
    print("\nApply tech 3 =>", verify2, "\n")
    print(T3.rule)    
    
#    ASTVisitor(Technique4(const, vars, metadata)).preorder(verify2.right)
#    ASTVisitor(SimplifyDotProducts()).preorder(verify2.right)
#    ASTVisitor(Technique3(const, vars)).preorder(verify2.right)    
    print("\nApply tech 4 =>", verify2, "\n")
        
    # Further precomputations
    #Instfind = InstanceFinder()
    #ASTVisitor(Instfind).preorder(verify2.right)
    #print("Instances found =>", Instfind.instance)
    
    #ASTVisitor(Substitute(Instfind.instance, precompute, vars)).preorder(verify2.right)
    #print("Precomputation =>", precompute)
    #print("Type information =>", vars)
    #print("\nFinal Equation =>", verify2)
    
    
    exit(0)
#    cg = CodeGenerator(const, vars, verify2.right)
#    result = cg.print_batchverify()
#    result = cg.print_statement(verify2.right)    
    #curve = {'a.param': {'pair': 1.90786, 'mul': {'GT': 0.00328, 'G2': 0.0092, 'G1': 0.0093, 'ZR':0}, 
    #                     'exp': {'GT': 0.37146, 'G2': 2.41154, 'G1': 2.40242, 'ZR':0}, 'hash':{'ZR':0, 'G1':0, 'G2':0, 'GT':0}}}
    #print("Python => '%s'" % result) # should be able to compile this
    try:
        import benchmarks
        curve = benchmarks.benchmarks
    except:
        print("Could not find the 'benchmarks' file that has measurement results! Generate and re-run.")
        exit(0)
    
    print("<===== Benchmark Results =====>")
    print("Assumption is N =", N)
    rop_ind = RecordOperations(vars)
    # add attrIndex to non constants
    ASTVisitor(ASTAddIndex(const, vars)).preorder(verify.right)
    print("<====\tINDIVIDUAL\t====>")
    print("Equation =>", verify.right)
    rop_ind.visit(verify.right, {'key':['N'], 'N': N })
    print("<===\tOperations count\t===>")
    print_results(rop_ind.ops)
    calculate_times(rop_ind.ops, curve['d224.param'], N)
    
    # Apply results on optimized batch algorithm
    rop_batch = RecordOperations(vars)
    rop_batch.visit(verify2.right, {})
    print("<====\tBATCH\t====>")    
    print("Equation =>", verify2.right)
    print("<===\tOperations count\t===>")
    print_results(rop_batch.ops)
    calculate_times(rop_batch.ops, curve['d224.param'], N)
    exit(0)
    
