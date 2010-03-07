# $Id: __init__.py 6153 2009-10-05 13:37:10Z milde $
# Author: James H. Fisher <jameshfisher@gmail.com>
# Copyright: This module has been placed in the public domain.

"""
Simple HyperText Markup Language 5 document tree Writer.

The output conforms to the HTML5 spec.

The output contains a minimum of formatting information.

The cascading style sheet "html5css3.css" is required
for proper viewing with a modern graphical browser.
"""

__docformat__ = 'reStructuredText'


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

# Suggested lxml import logic:
try:
  from lxml import etree
except ImportError:
  try:
    # Python 2.5
    import xml.etree.cElementTree as etree
  except ImportError:
    try:
      # Python 2.5
      import xml.etree.ElementTree as etree
    except ImportError:
      try:
        # normal cElementTree install
        import cElementTree as etree
      except ImportError:
        # normal ElementTree install
        import elementtree.ElementTree as etree

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

  supported = ('html', 'html5', 'html5css3')
  """Formats this writer supports."""

  default_stylesheet = 'html5css3.css'

  def __init__(self):
    writers.Writer.__init__(self)
    self.translator_class = HTML5Translator

  def translate(self):
    visitor = self.translator_class(self.document)
    self.document.walkabout(visitor)
    self.output = visitor.astext()


class HTML5Translator(nodes.NodeVisitor):

  doctype = "<!doctype html>"
  
  
  def astext(self):
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
    text = node.astext()
    
    e = self.cur_el()
    if len(e) == 0:
      e.text = text
    else:
      e[-1].tail = node.astext()
  def depart_Text(self, node):
    pass
  
  def visit_document(self, node):
    self.html = etree.Element("html")
    self.head = etree.SubElement(self.html, "head")
    self.body = etree.SubElement(self.html, "body")       # The body element everything is to be added to
    self.article = etree.SubElement(self.body, "article")
    self.section = self.article
    #self.header = etree.SubElement(self.article, "header")   # Meta-information goes here
    self.el = [self.article] # The current element
    
    httpequiv = etree.SubElement(self.head, "meta")
    httpequiv.set("http-equiv", "Content-Type")
    httpequiv.set("content", "text/html; charset=utf-8")  # % settings.output_encoding
    generator = etree.SubElement(self.head, "meta")
    generator.set("name", "generator")
    generator.set("content", "Docutils %s: http://docutils.sourceforge.net/" % docutils.__version__)
  
  def depart_document(self, node):
    pass
  
  def visit(self, name, **attrs):
    self.set_cur_el( etree.SubElement(self.cur_el(), name, **attrs) )
  def depart(self):
    self.set_cur_el( self.cur_el().getparent() )
  
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
    self.el.pop()
  
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
    self.el.pop()
  
  
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
        self.visit("th")
      else:
        self.visit("td")
    except AttributeError:
      self.visit("td")
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
  
    
simple_elements = {
  "paragraph": "p",
  "abbreviation": "abbr",
  "acronym": "acronym",
  "emphasis": "em",
  "strong": "strong",
  "table": "table",
  "tgroup": "tgroup",
  "row": "tr",
  "tbody": "tbody",
  "figure": "figure",
  "caption": "figcaption",
  "transition": "hr",
  "definition_list": "dl",
  "term": "dt",
  "definition": "dd"
  }
HTML5Translator.simple_elements = simple_elements

def depart_rst_name(self, node):
  self.depart()
def visit_rst_name_simple(self, node):
  self.visit(self.simple_elements[node.__class__.__name__]) # Something better than node.__class__.__name__
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
