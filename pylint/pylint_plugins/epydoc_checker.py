from logilab import astng

from pylint.interfaces import IASTNGChecker
from pylint.checkers import BaseChecker

from epydoc.markup import epytext

class EpyTextNode(object):
    def __init__(self, docString):
        docNode = epytext.parse(docString)
        self.docNode = docNode
        self.docString = docString

    def getDocumentedParameters(self):
        fields = self.getChild('fieldlist')
        params = []
        if not fields:
            return params
        for field in fields.children:
            tag = self.getChild('tag', field)
            if tag:
                tag = tag.children[0]
                if tag == 'param':
                    paramName = self.getChild('arg', field).children[0]
                    params.append(paramName)
                elif tag in ('type', 'return', 'rtype'):
                    continue
                else:
                    raise NotImplementedError('didnt see this case in testing')
            else:
                raise NotImplementedError('didnt see this case in testing')
        return params

    def getChild(self, tag, docNode=None):
        if docNode is None:
            docNode = self.docNode
        for child in docNode.children:
            if child.tag == tag:
                return child

class EpydocParamsMatchChecker(BaseChecker):
    name = 'epydoc'
    msgs = {'C0999': ('Documented parameters do not match actual parameters',
                      'Used the parameters listed in epytext for a function'
                      ' do not match the actual parameter names')}
    options = ()
    __implements__ = IASTNGChecker


    def visit_function(self, node, *args, **kw):
        if node.doc is None:
            return
        docParams = EpyTextNode(node.doc).getDocumentedParameters()
        if node.is_method() and node.type != 'staticmethod':
            neededParams = node.argnames[1:]
        else:
            neededParams = node.argnames
        if docParams != neededParams:
            self.add_message('C0999', node=node)

def register(linter):
    """required method to auto register this checker"""
    linter.register_checker(EpydocParamsMatchChecker(linter))