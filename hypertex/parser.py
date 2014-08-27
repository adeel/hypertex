__name__ = "parser"

import os
from codecs import open
from functools import reduce
import re
from lxml import etree

from hypertex import render
from hypertex.constants import PAR_TAGS, BLOCK_TAGS, INLINE_TAGS
from hypertex.util import dict_merge

def _register_error(message):
  print "Error: %s" % message

def _register_macros_from_file(macros, fname, config):
  src_dir = config["src_dir"]
  if not os.path.isdir(src_dir):
    _register_error("The given path %s is not a directory." % src_dir)
  fpath = "%s/%s" % (src_dir, fname)
  if not os.path.isfile(fpath):
    _register_error("A macro file could not be found at the path: %s" % fpath)
    return macros
  try:
    src = open(fpath, "r").read()
  except IOError:
    _register_error("Macros could not be loaded from the path: %s" % fpath)
    return macros
  root = etree.fromstring(src)
  return dict_merge(macros, dict([(x.attrib.get("name"), x.attrib.get("value"))
    for x in root.findall("macro")]))

def _register_refs_from_file(refs, fname, config):
  src_dir = config["src_dir"]
  if not os.path.isdir(src_dir):
    _register_error("The given path %s is not a directory." % src_dir)
  fpath = "%s/%s" % (src_dir, fname)
  if not os.path.isfile(fpath):
    _register_error("A reference file could not be found at the path: %s"
      % fpath)
    return refs
  try:
    src = open(fpath, "r").read()
  except IOError:
    _register_error("References could not be loaded from the path: %s" % fpath)
    return refs
  root = etree.fromstring(src)
  return dict_merge(refs,
    dict([(r.attrib.get("id"), dict([(x.tag, x.text) for x in r]))
      for r in root.findall("ref")]))

def _parse_head(head, config):
  title = head.find("title")
  author = head.find("author")
  
  macros = dict([(x.attrib.get("name"), x.attrib.get("value"))
    for x in head.findall("macro")])
  macro_files = [x.attrib.get("src", "") for x in head.findall("macros")]
  macros = reduce(lambda x,y: _register_macros_from_file(x, y, config),
    macro_files, macros)

  ref_files = [x.attrib.get("src", "") for x in head.findall("refs")]
  refs = reduce(lambda x,y: _register_refs_from_file(x, y, config),
    ref_files, {})

  return {"title":  title.text if title is not None else "",
          "author": author.text if author is not None else "",
          "macros": macros,
          "refs": refs}

def _parse_partag(tag):
  """
  Parse a paragraph tag into a pair (doc, par), where doc is the document
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

def _resolve_internal_partag(par_tag, parsed, config):
  """
  parsed = parse_htex(input)
  resolve_internal_tag("homotopy groups", parsed)
  # => 7
  resolve_internal_tag("Riemann hypothesis", parsed)
  # => None
  """
  all_tags = [p.get("tags", []) for p in parsed["body"]["pars"]]
  for (i, ts) in enumerate(all_tags):
    if par_tag in ts:
      return {"par": i + 1}

def _resolve_external_partag(doc, par, config):
  """
  Get the number of the par with tag `tag` in the document with name `doc`.
  Takes also the parameter `parsed`, which should be the result of parsing
  the current document, just in order to avoid re-parsing it.
  """
  src_dir = config["src_dir"]
  fpath = None
  if not os.path.isdir(src_dir):
    _register_error("The given path %s is not a directory." % src_dir)
  try:
    fpath = "%s/%s.xml" % (src_dir, doc)
    htex = open(fpath, encoding="utf8", mode="r").read()
    parsed = parse(htex, config)
  except:
    return {"doc": doc, "path": fpath, "par": 0}
  r = _resolve_internal_partag(par, parsed, config)
  if not r:
    _register_error("Could not resolve tag (%s, %s)." % (doc, par))
    return {"doc": doc, "path": fpath, "par": 0}
  return dict_merge(r, {"doc": doc, "path": fpath})

def _parse_citation_tag(element, config):
  ref = element.attrib.get("ref")
  tag = element.attrib.get("tag")
  pre = element.attrib.get("pre")
  post = element.attrib.get("post")
  if tag:
    x = {"type": "citation", "tag": tag, "pre": pre, "post": post}
    (doc, par) = _parse_partag(tag)
    if doc:
      return dict_merge(x, _resolve_external_partag(doc, par, config))
    else:
      # internal tag - will have to get it on second pass
      return x
  elif ref:
    return {"type": "external_citation",
      "refid": ref, "pre": pre, "post": post}

def _parse_term_tag(element, config):
  tag = element.attrib.get("tag", "")
  x = {"type": "term", "tag": tag}
  (doc, par) = _parse_partag(tag)
  if doc:
    return dict_merge(x, _resolve_external_partag(doc, par, config))
  else:
    # internal tag - will have to get it on second pass
    return x

def _parse_inline_tag(element, config):
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
    return _parse_citation_tag(element, config)
  elif element.tag == "term":
    return _parse_term_tag(element, config)
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
  elif element.tag == "sub":
    return {"type": "subscript"}
  elif element.tag == "sup":
    return {"type": "superscript"}

def _parse_node(element, config):
  """
  Parse a node (block tag or inline tag).
  Block tags are def, thm, prp, lem, cor, rmk, exm, prf.
  Inline tags are b, i, u, d, cite, term, frml.
  """
  content = (([element.text] if element.text else [])
    + sum([[_parse_node(child, config), child.tail or ""]
        for child in element], []))
  if element.tag in PAR_TAGS:
    return {"content": content}
  elif element.tag in BLOCK_TAGS:
    return {"type": element.tag, "content": content}
  elif element.tag in INLINE_TAGS:
    x = dict_merge(_parse_inline_tag(element, config), {"content": content})
    if x["type"] == "formula":
      # strip whitespace from beginning/end of formulas
      return dict_merge(x, {"content": map(str.strip, x["content"])})
    return x
  return {"content": content}

def _parse_body_pars(pars, element, config):
  if element.tag in PAR_TAGS:
    return pars + [{
      "type":    element.tag,
      "content": [_parse_node(element, config)],
      "tags":    element.attrib.get("tag", "").split(";")}]
  return pars

def _parse_body(body, config):
  return {"body": {"pars":
    reduce(lambda x,y: _parse_body_pars(x, y, config), body, [])}}

def _parse_first_gen(parsed, element, config):
  if element.tag == "head":
    return dict_merge(parsed, _parse_head(element, config))
  if element.tag == "body":
    return dict_merge(parsed, _parse_body(element, config))
  return parsed

def _fix_angle_brackets(htex):
  """
  A hack to make sure lxml doesn't complain about angle brackets
  that are not part of XML tags.
  """
  htex = re.sub(r"<(\s+)", r"&lt;\1", htex)
  htex = re.sub(r"([^a-z\"\/\-]+)>", r"\1&gt;", htex)
  return htex

def _resolve_internal_citations_in_node(node, parsed, config):
  if type(node) in (str, unicode):
    return node
  if (node.get("type") in ("citation", "term") and
      not node.get("doc") and not node.get("par")):
    (doc, par) = _parse_partag(node.get("tag"))
    if not doc:
      r = _resolve_internal_partag(par, parsed, config)
      if not r:
        r = {"par": 0}
      return dict_merge(node, r)
  return dict_merge(node, {"content":
    [_resolve_internal_citations_in_node(x, parsed, config) for x in node.get("content")]})

def _resolve_external_citations_in_node(node, cited_refs, parsed, config):
  if type(node) in (str, unicode):
    return {"cited_refs": cited_refs, "par": node}
  if (node.get("type") == "external_citation" and
      not node.get("ref")):
    ref = parsed["refs"].get(node.get("refid"), {})
    if ref:
      cited_refs.add(node.get("refid"))
    return {"cited_refs": cited_refs, "par": dict_merge(node, {"ref": ref})}
  resolved_content = []
  for x in node.get("content"):
    y = _resolve_external_citations_in_node(x, cited_refs, parsed, config)
    resolved_content.append(y["par"])
    cited_refs.update(y["cited_refs"])
  return {"cited_refs": cited_refs, "par": dict_merge(node, {"content": resolved_content})}

def parse(htex, config={}):
  config = dict_merge({"src_dir": "./"}, config)
  htex = _fix_angle_brackets(htex)
  root = etree.fromstring(htex)
  parsed = reduce(lambda x,y: _parse_first_gen(x,y,config), root, {})

  # second pass: resolve internal citations
  parsed["body"]["pars"] = map(lambda p:
    _resolve_internal_citations_in_node(p, parsed, config),
    parsed["body"]["pars"])
  # resolve external citations
  cited_refs = set()
  resolved_pars = []
  for p in parsed["body"]["pars"]:
    x = _resolve_external_citations_in_node(p, cited_refs, parsed, config)
    cited_refs.update(x.get("cited_refs"))
    resolved_pars.append(x.get("par"))
    # TODO: don't resolve the pars, just keep the ref id there
  parsed["body"]["pars"] = resolved_pars

  cited_refs = map(lambda x: dict_merge({"id": x}, parsed["refs"].get(x)), list(cited_refs))
  cited_refs = sorted(cited_refs, key=lambda x: (x.get("author"), x.get("title")))
  for (i, r) in enumerate(cited_refs):
    cited_refs[i] = dict_merge(r, {"key": str(i + 1)})
  parsed["refs"] = dict([(r["id"], r) for r in cited_refs])
  return parsed
