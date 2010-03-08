#! -*- coding: utf-8 -*-
# $Id: __init__.py 6153 2009-10-05 13:37:10Z milde $
# Author: James H. Fisher <jameshfisher@gmail.com>
# Copyright: This module has been placed in the public domain.

"""
Simple document tree Writer for HTML5.

The output contains a minimum of formatting information.

The cascading style sheet "html5css3.css" is required
for proper viewing with a modern graphical browser.
"""

__docformat__ = 'reStructuredText'

"""
CSS for this module is based on the following principles:

- don't override default browser representation of semantic elements (e.g. <cite>)
- don't use non-semantic classes (e.g. "list-style: lower-alpha" should be directly in the HTML 'style' attribute)
- Don't identify presentational aspects where CSS can; e.g. class="first" should instead use the :first-child pseudo-selector
- minimal in space (crush it if embedding)

"""

helper_css = u"""
/*body { font-family: Gentium Basic; width: 40em; margin: 0 auto 0 auto; }*/
.docutils dt { font-weight: bold; }
.docutils dd { margin-bottom: 1em; }
.docutils header th { text-align: left; padding-right: 1em;}
.docutils header th:after { content: ":"; }
.docutils hgroup *:first-child { margin-bottom: 0;}
.docutils hgroup *:nth-child(2) { margin-top: 0; }
.docutils table.option-list th { font-weight: normal; vertical-align: top; text-align: left; }
.docutils table.option-list th span { margin: 0; padding: 0; }
"""



"""
Std lib imports
```````````````
"""

import sys
import os
import os.path
import time
import re


"""
Other lib imports
`````````````````
"""

try:
    import Image # check for the Python Imaging Library
except ImportError:
    Image = None

from lxml import html as lxmlhtml
from lxml import etree


try:
  from dateutil.parser import parse as dateutil_date_string_parse
except ImportError:
  def date_string_parse(s):
    raise ValueError("dateutil library not found")
else:
  def date_string_parse(s):
    return dateutil_date_string_parse(s).isoformat()

"""
Docutils imports
````````````````
"""

import docutils
from docutils import frontend, nodes, utils, writers, languages
from docutils.transforms import writer_aux


class Writer(writers.Writer):

  supported = ('html', 'html5', 'html5css3')  # Formats this writer supports

  def __init__(self):
    writers.Writer.__init__(self)
    self.translator_class = HTML5Translator

  def translate(self):
    visitor = self.translator_class(self.document)
    self.document.walkabout(visitor)
    self.output = visitor.astext()

def add_text(node, text):
  if len(node):
    if node[-1].tail == None:
      node[-1].tail = ""
    node[-1].tail += text
  else:
    if node.text == None:
      node.text = ""
    node.text += text

class HTML5Translator(nodes.NodeVisitor):

  doctype = "<!doctype html>"
  
  
  def astext(self):
    compact(self.html)
    return self.doctype + "\n" + etree.tostring(self.html, pretty_print=True)

  def cloak_mailto(self, uri):
    """Try to hide a mailto: URL from harvesters."""
    # Encode "@" using a URL octet reference (see RFC 1738).
    # Further cloaking with HTML entities will be done in the
    # `attval` function.
    return uri.replace('@', '%40')

  def cloak_email(self, addr):
    """Try to hide the link text of a email link from harvesters."""
    # Surround at-signs and periods with <span> tags.  ("@" has
    # already been encoded to "&#64;" by the `encode` method.)
    addr = addr.replace('&#64;', '<span>&#64;</span>')
    addr = addr.replace('.', '<span>&#46;</span>')
    return addr
  
  def cur_el(self):
    return self.el[-1]
  
  def set_cur_el(self, val):
    self.el[-1] = val
  
  def visit_Text(self, node):
    add_text(self.cur_el(), node.astext())
  
  def depart_Text(self, node):
    pass
  
  def visit_document(self, node):
    self.html = etree.Element("html")
    self.head = etree.SubElement(self.html, "head")
    self.body = etree.SubElement(self.html, "body")       # The body element everything is to be added to
    self.article = etree.SubElement(self.body, "article")
    self.article.set("class", "docutils") # Namespacing everything for the CSS
    self.section = self.article
    #self.header = etree.SubElement(self.article, "header")   # Meta-information goes here
    self.el = [self.article] # The current element
    
    self.add_meta("generator", "Docutils %s: http://docutils.sourceforge.net/" % docutils.__version__)
    
    etree.SubElement(self.head, "style", type="text/css").text = helper_css
  
  def depart_document(self, node):
    pass
  
  def visit(self, name, **attrs):
    self.set_cur_el( etree.SubElement(self.cur_el(), name, **attrs) )
    return self.cur_el()
  def depart(self):
    self.set_cur_el( self.cur_el().getparent() )
  
  def add(self, name, **attrs):
    return etree.SubElement(self.cur_el(), name, **attrs)
    
  def local_header(self):
    # Get the appropriate header for attaching titles or docinfo
    tmp = self.cur_el()
    while True:
      if tmp.tag in ("section", "article"):
        headers = tmp.xpath('header')
        if len(headers) > 0:
          header = headers[0]
        else:
          header = etree.SubElement(tmp, "header")
        return header
      else:
        # Go up one
        parent = tmp.parent()
        if parent == tmp:
          # Shouldn't happen
          return None
        else:
          tmp = parent
  
  def add_meta(self, attr, val):
    etree.SubElement(self.html.xpath("/html/head")[0], "meta", attrib={'name': attr, 'content': val})
  
  def visit_title(self, node):
    try:
      self.level
    except AttributeError:
      self.level = 1
    else:
      self.level += 1
    hgroup = etree.SubElement(self.local_header(), "hgroup")
    self.el.append(etree.SubElement(hgroup, "h" + str(self.level)))
  def depart_title(self, node):
    self.el.pop()
  
  def visit_subtitle(self, node):
    self.el.append(etree.SubElement(self.local_header().xpath("hgroup")[0], "h"+ str(self.level+1)))
  def depart_subtitle(self, node):
    self.el.pop()
  
  def visit_section(self, node):
    self.visit("section")
  def depart_section(self, node):
    self.level -= 1
    self.depart()
  
  def visit_docinfo(self, node):
    self.local_header().set("itemscope", "true")
  def depart_docinfo(self, node):
    pass
  
  def local_docinfo(self):
    local_header = self.local_header()
    tbodies = local_header.xpath("table/tbody")
    if len(tbodies) > 0:
      return tbodies[0]
    return etree.SubElement(etree.SubElement(local_header, "table"), "tbody")
  
  def prep_docinfo(self, human, machine):
    tr = etree.SubElement(self.local_docinfo(), "tr")
    etree.SubElement(tr, "th").text = human
    return etree.SubElement(tr, "td", itemprop=machine)
  
  def visit_author(self, node):
    self.el.append(self.prep_docinfo("Author", "author"))
  def depart_author(self, node):
    el = self.el.pop()
    self.add_meta("author", el.text)
  
  def visit_date(self, node):
    self.el.append(self.prep_docinfo("Date", "date"))
    self.visit("time")
    try:
      iso_date = date_string_parse( node.children[0].astext() )
    except ValueError:
      pass
    else:
      self.cur_el().set("datetime", iso_date)
  def depart_date(self, node):
    time = self.el.pop()
    self.add_meta("date", time.get("datetime", time.text))
  
  
  def visit_colspec(self, node):
    pass
  def depart_colspec(self, node):
    pass
  
  def visit_thead(self, node):
    self.visit("thead")
    self.in_thead = True
  def depart_thead(self, node):
    self.depart()
    self.in_thead = False
  
  def visit_entry(self, node):
    try:
      if self.in_thead:
        el = self.visit("th")
      else:
        el = self.visit("td")
    except AttributeError:
      el = self.visit("td")
    rowspan = node.attributes.get('morerows', 0) + 1
    colspan = node.attributes.get('morecols', 0) + 1
    if rowspan > 1:
      el.set("rowspan", str(rowspan))
    if colspan > 1:
      el.set("colspan", str(colspan))
      
  def depart_entry(self, node):
    self.depart()
  
  def visit_image(self, node):
    self.visit("img")
    self.cur_el().set("src", node.attributes['uri'])
  def depart_image(self, node):
    self.depart()
  
  def visit_definition_list_item(self, node):
    pass
  def depart_definition_list_item(self, node):
    pass
  
  def visit_block_quote(self, node):
    self.visit("blockquote")
    self.visit("section")
  def depart_block_quote(self, node):
    if not self.cur_el()[-1].tag == "cite":
      self.depart()
    self.depart()
  
  def visit_attribution(self, node):
    self.depart() # The section
    self.visit("cite")
  def depart_attribution(self, node):
    self.depart()
  
  def visit_enumerated_list(self, node):
    el = self.visit("ol")
    html_list_style = {
      'arabic':       None, # Default. Don't bother specifying it; it just makes ugly HTML.
      'loweralpha':  'lower-alpha',
      'upperalpha':  'upper-alpha',
      'lowerroman':  'lower-roman',
      'upperroman':  'upper-roman',
      }[node.attributes['enumtype']]
    if html_list_style:
      el.set("style", "list-style: %s;" % html_list_style)
  def depart_enumerated_list(self, node):
    self.depart()
  
  def visit_option_argument(self, node):
    el = self.visit("span")
    el.set("class", "option-delimiter")
    el.text = node.attributes['delimiter']
    self.depart()
    el = self.visit("var")
  def depart_option_argument(self, node):
    self.depart()
  
  def visit_option_group(self, node):
    self.visit("th")
    self.visit("kbd")
  def depart_option_group(self, node):
    self.depart()
    self.depart()
  
  def visit_line_block(self, node):
    try:
      self.line_block_indent
    except AttributeError:
      self.line_block_indent = -1
    self.line_block_indent += 1
  def depart_line_block(self, node):
    self.line_block_indent -= 1
  
  def visit_line(self, node):
    el = self.cur_el()
    add_text(el, u" " * (self.line_block_indent * 4))
  def depart_line(self, node):
    self.add("br")
  
class Tag:
  def __init__(self, html_tag_name, classes=None, attribute_map={}):
    self.html_tag_name = html_tag_name
    self.classes = classes
    self.attribute_map = attribute_map

simple_elements = {         # HTML equiv.   
  "paragraph":        Tag(  "p"                                         ),
  "abbreviation":     Tag(  "abbr",                                     ),
  "acronym":          Tag(  "acronym",                                  ),
  "emphasis":         Tag(  "em",                                       ),
  "strong":           Tag(  "strong",                                   ),
  "table":            Tag(  "table",                                    ),
  "tgroup":           Tag(  "tgroup",                                   ),
  "row":              Tag(  "tr",                                       ),
  "tbody":            Tag(  "tbody",                                              ),                     
  "image":            Tag(  "img",        attribute_map={"uri": "src", "alt": "alt"},         ),
  "figure":           Tag(  "figure",                                   ),
  "caption":          Tag(  "figcaption",                               ),
  "transition":       Tag(  "hr",                                       ),
  "definition_list":  Tag(  "dl",                                       ),
  "term":             Tag(  "dt",                                       ),
  "definition":       Tag(  "dd",                                       ),
  "literal_block":    Tag(  "pre",                                      ),
  "bullet_list":      Tag(  "ul",                                       ),
  "list_item":        Tag(  "li",                                       ),
  "option_list":      Tag(  "table",    "option-list"                   ),
  "option_list_item": Tag(  "tr"),
  "option":           Tag(  "span"),
  "option_string":    Tag(  "span", "option"),
  "description":      Tag("td"),
  }
    
HTML5Translator.simple_elements = simple_elements

def depart_rst_name(self, node):
  self.depart()
def visit_rst_name_simple(self, node):
  simple_element = self.simple_elements[node.__class__.__name__]
  cur_el = self.visit(simple_element.html_tag_name)
  if simple_element.classes:
    cur_el.set("class", simple_element.classes)
  for k in simple_element.attribute_map.keys():
    attr = node.attributes.get(k, None)
    if attr:
      cur_el.set(simple_element.attribute_map[k], attr)
  
for rst_name in simple_elements.keys():
  setattr(HTML5Translator, "visit_" + rst_name, visit_rst_name_simple)
  setattr(HTML5Translator, "depart_" + rst_name, depart_rst_name)

classy_elements = ["topic"]
HTML5Translator.classy_elements = classy_elements

def visit_rst_name_classy(self, node):
  self.visit("div", **{'class':self.classy_elements[node.__class__.__name__]})  # Can't use 'class' directly; it's a keyword
for rst_name in classy_elements:
  setattr(HTML5Translator, "visit_" + rst_name, visit_rst_name_classy)
  setattr(HTML5Translator, "depart_" + rst_name, depart_rst_name)



def compact(html_tree):
  """
  Given an HTML tree, compact it.  This involves:
  
  - finding all nodes with a single non-text child node
  - checking the pair (parent, child) in following lists,
    and it is in the list, replace the pair with the appropriate
    element of the two:
    
    Replace with parent:
    *, p
    
    Replace with child:
    hgroup, h*
  """
  for p in html_tree.xpath("//p"):
    parent = p.getparent()
    if len(parent) == 1 and parent.text == None:
      parent.text = p.text
      for c in p:
        parent.append(c)
      parent.remove(p)
      
