#!/usr/ali/bin/python
# coding=utf-8

"""Classes to generate HTML in Python

The HTMLTags module defines a class for all the valid HTML tags, written in
uppercase letters. To create a piece of HTML, the general syntax is :
    t = TAG(content, key1=val1,key2=val2,...)

so that "print t" results in :
    <TAG key1="val1" key2="val2" ...>content</TAG>

For instance :
    print A('bar', href="foo") ==> <A href="foo">bar</A>

To generate HTML attributes without value, give them the value True :
    print OPTION('foo',SELECTED=True,value=5) ==> 
            <OPTION value="5" SELECTED>

The content argument can be an instance of an HTML class, so that 
you can nest tags, like this :
    print B(I('foo')) ==> <B><I>foo</I></B>

TAG instances support addition :
    print B('bar')+INPUT(name="bar") ==> <B>bar</B><INPUT name="bar">

and repetition :
    print TH('&nbsp')*3 ==> <TD>&nbsp;</TD><TD>&nbsp;</TD><TD>&nbsp;</TD>

For complex expressions, a tag can be nested in another using the operator <= 
Considering the HTML document as a tree, this means "add child" :

    form = FORM(action="foo")
    form <= INPUT(name="bar")
    form <= INPUT(Type="submit",value="Ok")

If you have a list (or any iterable) of instances, you can't concatenate the 
items with sum(instance_list) because sum takes only numbers as arguments. So 
there is a function called Sum() which will do the same :

    Sum( TR(TD(i)+TD(i*i)) for i in range(100) )

generates the rows of a table showing the squares of integers from 0 to 99

A simple document can be produced by :
    print HTML( HEAD(TITLE('Test document')) +
        BODY(H1('This is a test document')+
             'First line'+BR()+
             'Second line'))

If the document is more complex it is more readable to create the elements 
first, then to print the whole result in one instruction. For example :

head = HEAD()
head <= TITLE('Record collection')
head <= LINK(rel="Stylesheet",href="doc.css")

title = H1('My record collection')
table = TABLE()
table <= TR(TH('Title')+TH('Artist'))
for rec in records:
    row = TR()
    # note the attribute key Class with leading uppercase 
    # because "class" is a Python keyword
    row <= TD(rec.title,Class="title")+TD(rec.artist,Class="artist")
    table <= row

print HTML(head+BODY(title+table))

Content or attribute value can be Unicode strings. The __str__
method will convert them to a bytestring using the value in the
attribute output_encoding of current thread. It can be changed 
with the function set_encoding()

See http://karrigell.sourceforge.net/en/htmltags.html for more help.

# Added by tuantuan
1. create a table
tbl = create_table([['h1', 'h2', 'h3'],             # table hader
    ['r11', 'r12', 'r13'], ['r21', 'r22', 'r23']],  # table rows
    'a test for creating table')                    # table caption

2. create a list
lst = create_list(['first row', 'second row', 'third row'],  # list rows
    'a test for creating list')                              # list caption

See test_main() for more examples.
"""

import sys
import cStringIO
import threading

# encoding is thread-specific (in a multi-thread web server, each request
# may use a different encoding)
threading.currentThread().output_encoding = sys.getdefaultencoding()

def set_encoding(encoding):
    threading.currentThread().output_encoding = encoding

def to_unicode(data):
    return data.encode(threading.currentThread().output_encoding)

class TAG:
    """Generic class for tags"""
    def __init__(self, *content, **attrs):
        self.tag = self.__class__.__name__
        self.attrs = attrs
        # we can't init with argument content='' because of conflict
        # if a key 'content' is in **attrs
        if not content:
            self.children = []
        elif len(content)>1:
            raise ValueError('%s takes only one positional argument' %self.tag)
        elif isinstance(content[0],TAG) and content[0].__class__ is TAG: 
            # abstract class with no parent
            self.children = content[0].children
        else:
            self.children = [content[0]]
        self._update_parent()

    def _update_parent(self):
        for child in self.children:
            if isinstance(child,TAG):
                child.parent = self

    def __str__(self):
        import sys
        res=cStringIO.StringIO()
        w=res.write
        if self.tag not in ["TAG","TEXT"]:
            w("<%s" %self.tag.lower())
            # attributes which will produce arg = "val"
            attr1 = [ k for k in self.attrs 
                if not isinstance(self.attrs[k],bool) ]
            attr_list = []
            for k in attr1:
                key = k.replace('_','-')
                value = self.attrs[k]
                if isinstance(value,unicode):
                    value = to_unicode(value)
                attr_list.append(' %s="%s"' %(key.lower(),value))
            w("".join(attr_list))
            # attributes with no argument
            # if value is False, don't generate anything
            attr2 = [ k for k in self.attrs if self.attrs[k] is True ]
            w("".join([' %s' %k.lower() for k in attr2]))
            w(">")
        if self.tag in _ONE_LINE:
            w('\n')
        for child in self.children:
            if isinstance(child,unicode):
                w(to_unicode(child))
            else:
                w('%s' % child)
        if self.tag in _CLOSING_TAGS:
            w("</%s>" %self.tag.lower())
        if self.tag in _LINE_BREAK_AFTER:
            w('\n')
        return res.getvalue()
    
    def __le__(self,other):
        """Add a child"""
        if other.__class__ is TAG:
            self.children += other.children
        else:
            if isinstance(other,str):
                other = TEXT(other)
            self.children.append(other)
        return self

    def __add__(self,other):
        """Return a new instance : concatenation of self and another tag"""
        if self.__class__ is TAG:
            if other.__class__ is TAG:
                self.children += other.children
            else:
                self.children.append(other)
            self._update_parent()
            return self
        else:
            res = TAG() # abstract tag
            res.children = [self,other]
            res._update_parent()
            return res

    def __radd__(self,other):
        """Used to add a tag to a string"""
        if isinstance(other,(unicode,str)):
            return TEXT(other)+self
        else:
            raise ValueError,"Can't concatenate %s and instance" %other

    def __mul__(self,n):
        """Replicate self n times, with tag first : TAG * n"""
        res = TAG()
        res.children = [self for i in range(n)]
        return res

    def __rmul__(self,n):
        """Replicate self n times, with n first : n * TAG"""
        return self*n

    def __getitem__(self,attr):
        return self.attrs[attr]
    
    def __setitem__(self,key,value):
        self.attrs[key] = value

    def get_by_attr(self,**kw):
        """Return a list of tags whose attributes are in kw,
        at the same level as self or below in the tree"""
        res = []
        flag = True
        for k,v in kw.iteritems():
            if self.attrs.get(k,None) !=v:
                flag = False
                break
        if flag:
            res.append(self)
        for child in self.children:
            if isinstance(child,TAG):
                res += child.get_by_attr(**kw)
        return _tag_list(res)

    def get_by_tag(self,tag_name):
        """Return a list of tags of specified tag name,
        at the same level as self or below in the tree"""
        res = []
        if self.tag == tag_name:
            res.append(self)
        for child in self.children:
            if isinstance(child,TAG):
                res += child.get_by_tag(tag_name)
        return _tag_list(res)

    def get(self,*tags,**kw):
        """Search instances of classes in tags with attributes = kw"""
        res = []
        if not tags or self.__class__ in tags:
            flag = True
            for (k,v) in kw.items():
                if k not in self.attrs or v != self.attrs[k]:
                    flag = False
            if flag:
                res.append(self)
        for child in self.children:
            if isinstance(child,TAG):
                res+= child.get(*tags,**kw)
        return res

    def delete(self,subtag):
        subtag.parent.children.remove(subtag)

class _tag_list(list):

    def set_attr(self,**kw):
        for item in self:
            for key,value in kw.iteritems():
                item[key] = value

# list of tags, from the HTML 4.01 specification

_CLOSING_TAGS =  ['A', 'ABBR', 'ACRONYM', 'ADDRESS', 'APPLET',
            'B', 'BDO', 'BIG', 'BLOCKQUOTE', 'BUTTON',
            'CAPTION', 'CENTER', 'CITE', 'CODE',
            'DEL', 'DFN', 'DIR', 'DIV', 'DL',
            'EM', 'FIELDSET', 'FONT', 'FORM', 'FRAMESET',
            'H1', 'H2', 'H3', 'H4', 'H5', 'H6',
            'I', 'IFRAME', 'INS', 'KBD', 'LABEL', 'LEGEND',
            'MAP', 'MENU', 'NOFRAMES', 'NOSCRIPT', 'OBJECT',
            'OL', 'OPTGROUP', 'PRE', 'Q', 'S', 'SAMP',
            'SCRIPT', 'SMALL', 'SPAN', 'STRIKE',
            'STRONG', 'STYLE', 'SUB', 'SUP', 'TABLE',
            'TEXTAREA', 'TITLE', 'TT', 'U', 'UL',
            'VAR', 'BODY', 'COLGROUP', 'DD', 'DT', 'HEAD',
            'HTML', 'LI', 'P', 'TBODY','OPTION', 
            'TD', 'TFOOT', 'TH', 'THEAD', 'TR']

_NON_CLOSING_TAGS = ['AREA', 'BASE', 'BASEFONT', 'BR', 'COL', 'FRAME',
            'HR', 'IMG', 'INPUT', 'ISINDEX', 'LINK',
            'META', 'PARAM']

# create the classes
for _tag in _CLOSING_TAGS + _NON_CLOSING_TAGS + ['TEXT']:
    exec("class %s(TAG): pass" %_tag)

# Convenience methods for SELECT tags, radio and checkbox INPUT tags

def _check_args(**kw):
    # check if arguments are valid for selection or check methods
    if not kw:
        raise ValueError,'No arguments provided'
    elif len(kw.keys())>1:
        msg = 'Function takes 1 argument, %s provided'
        raise ValueError,msg %len(kw.keys())
    elif kw.keys()[0] not in ['content','value']:
        msg ='Bad argument %s, must be "content" or "value"'
        raise ValueError,msg %kw.keys()[0]
    return kw.keys()[0],kw.values()[0]

# SELECT has special methods to build a list of OPTION tags from
# a list, and marks one of several OPTION tags as selected
_CLOSING_TAGS.append('SELECT')

class SELECT(TAG):

    def from_list(self,_list,use_content=False):
    # build a SELECT tag from a list
        if not use_content:
            # values are content's rank
            self.children = [OPTION(item,value=i,SELECTED=False) 
                for (i,item) in enumerate(_list)]
        else:
            # values are content's value
            self.children = [OPTION(item,value=item,SELECTED=False) 
                for item in _list]
        return self

    def select(self,**kw):
    # mark an option (or several options if attribute MULTIPLE is set) as selected
        key,attr = _check_args(**kw)
        if not isinstance(attr,(list,tuple)):
            attr = [attr]
        if key == 'content':
            for option in self.children:
                option.attrs['SELECTED'] = option.children[0] in attr
        elif key == 'value':
            for option in self.children:
                option.attrs['SELECTED'] = option.attrs['value'] in attr

# Classes to build a list of radio and checkbox INPUT tags from a list
# of strings. All INPUT tags have the same attributes, including name
# and except the value, which is the string index in the list

# Instances of RADIO and CHECKBOX have a check() method, used to mark
# INPUT tags as checked. The argument can be a string value (or a list
# of strings) to check the tags associated with one of the items in the
# list, or an index (or a list of indices)

class RADIO:

    def __init__(self,_list,_values=None,**attrs):
        self._list = _list
        if _values is None :
            self.tags = [INPUT(Type="radio",value=i,checked=False,**attrs)
                    for i in range(len(_list))]
        else:
            if not isinstance(_values, (list, tuple)) :
                raise TypeError, "_values must be a list or a tuple"
            if len(_list) != len(_values) :
                raise ValueError, "len(_list) != len(_values)"
            self.tags = [INPUT(Type="radio",value=i,checked=False,**attrs)
                    for i in _values]

    def check(self,**kw):
        key,attr = _check_args(**kw)
        if key == 'content':
            for i,item in enumerate(self._list):
                self.tags[i].attrs['checked'] = self._list[i] == attr
        else:
            for (i,tag) in enumerate(self.tags):
                self.tags[i].attrs['checked'] = tag.attrs['value'] == attr

    def __iter__(self):
        return iter(zip(self._list,self.tags))

class CHECKBOX:

    def __init__(self,_list,_values=None,**attrs):
        self._list = _list
        if _values is None :
            self.tags = [INPUT(Type="checkbox",value=i,checked=False,**attrs)
                    for i in range(len(_list))]
        else:
            if not isinstance(_values, (list, tuple)) :
                raise TypeError, "_values must be a list or a tuple"
            if len(_list) != len(_values) :
                raise ValueError, "len(_list) != len(_values)"
            self.tags = [INPUT(Type="checkbox",value=i,checked=False,**attrs)
                    for i in _values]
            

    def check(self,**kw):
        key,attr = _check_args(**kw)
        if not isinstance(attr,(tuple,list)):
            attr = [attr]
        if key == 'content':
            for i,item in enumerate(self._list):
                self.tags[i].attrs['checked'] = self._list[i] in attr
        else:
            for (i,tag) in enumerate(self.tags):
                self.tags[i].attrs['checked'] = tag.attrs['value'] in attr

    def __iter__(self):
        return iter(zip(self._list,self.tags))

def Sum(iterable):
    """Return the concatenation of the instances in the iterable
    Can't use the built-in sum() on non-integers"""
    it = [ item for item in iterable ]
    if it:
        return reduce(lambda x,y:x+y, it)
    else:
        return ''

# whitespace-insensitive tags, determines pretty-print rendering
_LINE_BREAK_AFTER = _NON_CLOSING_TAGS + ['HTML','HEAD','BODY',
    'FRAMESET','FRAME',
    'TITLE','SCRIPT',
    'TABLE','TBODY','THEAD','TR','TD','TH','SELECT','OPTION',
    'FORM',
    'H1', 'H2', 'H3', 'H4', 'H5', 'H6',
    'UL','LI','OL','EM'
    ]
# tags whose opening tag should be alone in its line
_ONE_LINE = ['HTML','HEAD','BODY',
    'FRAMESET'
    'SCRIPT',
    'TABLE','TBODY','THEAD','TR',#'TD','TH',
    'SELECT',#'OPTION',
    'FORM','UL','OL'
    ]

######################### Added by tuantuan.lv #############################

def create_style(id = ''):
    '''Create a customized css style.
       
    The parameter id is the container's id if exists, otherwise leave it empty.
    Id selector has a bigger priority than others.
    '''
    if id != '':
        id = '#%s ' % id

    css_str = '''
%(id)sdiv {
  margin:10px 0 25px;
  font-size:12px;
  font-family: Verdana, Helvetica, sans-serif;
}

%(id)stable {
  font-family: Verdana, Helvetica, sans-serif;
  font-size: 12px;
  text-align:left;
  border-collapse:collapse;
  border: 1px solid #CCC;
}

%(id)sth {
  color: #F0F0F0;
  cursor: pointer;
  background-color: #07B;
  font-weight: bold;
}

%(id)sth, %(id)std {
  height:20px;
  padding:4px;
  word-wrap:break-word;
  border: 1px solid #CCC;
}

%(id)std {
  color:#3D3D3D;
  background:#FFF;
}

%(id)s.even-row { background-color:#F0F0F0; }

%(id)sp {
  font-size:14px;
  font-family: Verdana, Helvetica, sans-serif;
  margin-bottom:15px;
}

%(id)s.bold { font-weight:bold; }

%(id)sul, %(id)sol {
  font-size:12px;
  font-family: Verdana, Helvetica, sans-serif;
}

%(id)shr {
  margin: 10px 0;
  color:#CBCBCB;
}

%(id)sli {
  list-style:inside square;
  margin:2px 0 2px -15px;
}''' % {'id': id}

    return STYLE(css_str, type='text/css')
    
def create_seperator():
    '''Create a horizontal line.'''
    return HR('')

def create_table(rows, caption = None, has_header = True):
    '''Create a table.'''
    tbl = TABLE(cellspacing=0, cellpadding=1, border=0)

    if has_header: # Add the first row as the table header
        tbl_header = THEAD()
        tbl_header <= TR(Sum(TH(i) for i in rows[0]))
        tbl <= tbl_header

    tbl_body = TBODY()
    row_cnt = 1

    for row in rows[1:]: # Add the remaining rows as the table row 
        if row_cnt % 2 == 0:  # Apply even td css
            cls = 'even-row'
        else:  # Apply odd td css
            cls = 'odd-row'

        tr = TR()

        for i in row:
            attrs = {'Class': cls}

            # If element is a list or tuple, consider it as (value, rowspan, colspan),
            # which represents span rows or cols cell.
            if isinstance(i, list) or isinstance(i, tuple):
                i, rowspan, colspan = i

                if rowspan > 0:
                    attrs['rowspan'] = rowspan

                if colspan > 0:
                    attrs['colspan'] = colspan

            tr <= TD(i, **attrs)

        tbl_body <= tr
        row_cnt += 1

    tbl <= tbl_body

    if caption is not None: # Add the table caption if given
        tbl = P('-TABLE- %s' % caption, Class='bold') + tbl

    return tbl

def create_list(rows, caption = None, ordered = False):
    '''Create a list.'''
    if ordered:
        lst = OL()
    else:
        lst = UL()

    for row in rows: # Add all rows to list
        lst <= LI(row)

    if caption is not None: # Add the list caption if given
        lst = P('-LIST- %s' % caption, Class='bold') + lst

    return lst

def test_main():
    outer = DIV()
    outer <= create_style('inner')

    inner = DIV(id='inner')
    outer <= inner

    inner <= create_list(['first row', 'second row', 'third row'],  # list rows
        'a test for creating list')                              # list caption

    inner <= create_seperator()

    inner <= create_table([['h1', 'h2', 'h3'],             # table hader
        ['r11', 'r12', 'r13'], ['r21', 'r22', 'r23']],  # table rows
        'a test for creating table')                    # table caption

    inner <= create_seperator()

    inner <= create_table([['h1', 'h2', 'h3'],             # table hader
        [('r11中文', 2, 0), 'r12', 'r13'], ['r22', 'r23']], # Span rows cell
        'a test for creating table')                    # table caption

    print outer

if __name__ == '__main__':
    test_main()
