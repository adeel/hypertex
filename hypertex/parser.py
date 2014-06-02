__name__ = "parser"

import os
from functools import reduce
import re
from lxml import etree

from hypertex import render
from hypertex.constants import PAR_TAGS, BLOCK_TAGS, INLINE_TAGS
from hypertex.util import dict_merge

def _register_error(message):
  print "Error: %s" % message

def _register_macros_from_file(macros, fname):
  if not os.path.isfile(fname):
    _register_error("The macro file %s was not found and will not be loaded." % fname)
    return macros
  try:
    src = open(fname, "r").read()
  except IOError:
    _register_error("The macro file %s could not be read and will not be loaded." % fname)
    return macros
  root = etree.fromstring(src)
  return dict_merge(macros, dict([(x.attrib.get("name"), x.attrib.get("value"))
    for x in root.findall("macro")]))

def _parse_head(head):
  title = head.find("title")
  author = head.find("author")
  macros = dict([(x.attrib.get("name"), x.attrib.get("value"))
    for x in head.findall("macro")])
  macro_files = [x.attrib.get("src", "") for x in head.findall("macros")]
  macros = reduce(_register_macros_from_file, macro_files, macros)

  return {"title":  title.text if title is not None else "",
          "author": author.text if author is not None else "",
          "macros": macros}

def _parse_inline_tag(element):
  "Return the type of an inline tag (e.g. b => bold)."

  if element.tag == "b":
    return {"type": "bold"}
  elif element.tag == "i":
    return {"type": "italic"}
  elif element.tag == "u":
    return {"type": "underline"}
  elif element.tag == "d":
    return {"type": "definition"}
  elif element.tag == "cite":
    return {"type": "citation",
      "ref": element.attrib.get("ref"),
      "tag": element.attrib.get("tag")}
  elif element.tag == "term":
    return {"type": "term",
      "tag": element.attrib.get("tag")}
  elif element.tag == "frml":
    img = False
    if element.attrib.get("img"):
      img = True
    return {"type": "formula", "img": img}
  elif element.tag == "ol":
    return {"type": "ord_list"}
  elif element.tag == "ul":
    return {"type": "unord_list"}
  elif element.tag == "li":
    return {"type": "list_item"}

def _parse_node(element):
  """
  Parse a node (block tag or inline tag).
  Block tags are def, thm, prp, lem, cor, rmk, exm, prf.
  Inline tags are b, i, u, d, cite, term, frml.
  """

  content = (([element.text] if element.text else [])
    + sum([[_parse_node(child), child.tail or ""] for child in element], []))
  if element.tag in PAR_TAGS:
    return {"content": content}
  elif element.tag in BLOCK_TAGS:
    return {"type": element.tag, "content": content}
  elif element.tag in INLINE_TAGS:
    x = dict_merge(_parse_inline_tag(element), {"content": content})
    if x["type"] == "formula":
      # strip whitespace from beginning/end of formulas
      x = dict_merge(x, {"content": map(str.strip, x["content"])})
    return x
  return {"content": content}

def _parse_body_pars(pars, element):
  if element.tag in PAR_TAGS:
    return pars + [{
      "type":    element.tag,
      "content": [_parse_node(element)],
      "tags":    element.attrib.get("tag", "").split(";")}]
  return pars

def _parse_body(body):
  return {"body": {"pars": reduce(_parse_body_pars, body, [])}}

def _parse_first_gen(parsed, element):
  if element.tag == "head":
    return dict_merge(parsed, _parse_head(element))
  if element.tag == "body":
    return dict_merge(parsed, _parse_body(element))
  return parsed

def _fix_angle_brackets(htex):
  """
  A hack to make sure lxml doesn't complain about angle brackets
  that are not part of XML tags.
  """
  htex = re.sub(r"<(\s+)", r"&lt;\1", htex)
  htex = re.sub(r"([^a-z\"\/\-]+)>", r"\1&gt;", htex)
  return htex

def parse(htex):
  htex = _fix_angle_brackets(htex)
  root = etree.fromstring(htex)
  return reduce(_parse_first_gen, root, {})

def parse_tag(tag):
  """
  Parse a tag into a pair (doc, par), where doc is the document
  identifier and partag is the paragraph identifier.
  """
  (doc, par) = ("", "")
  tag_parts = tag.split("/")
  if len(tag_parts) == 1:
    par = tag_parts[0]
  else:
    doc = tag_parts[0]
    par = tag_parts[1]
  return (doc, par)

def get_number_of_par(tag, doc, parsed):
  """
  Get the number of the par with tag `tag` in the document with name `doc`.
  Takes also the parameter `parsed`, which should be the result of parsing
  the current document, just in order to avoid re-parsing it.
  """
  if doc:
    try:
      src = open(doc + ".xml", "r").read()
      parsed = parse_texml(src)
    except:
      return 0
  doc_tags = [p.get("tags", []) for p in parsed.get("body").get("pars")]
  for (n, ts) in enumerate(doc_tags):
    if tag in ts:
      return n + 1
  _register_error("Unable to find tag %s in document '%s'" % (tag, doc))
  return 0
