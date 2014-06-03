__name__ = "tex"

import os.path
from jinja2 import Environment, PackageLoader

from hypertex.constants import BLOCK_TAGS
from hypertex.util import dict_merge

tmpl_env = Environment(loader=PackageLoader("hypertex.render", "tex"))

def _render_content(node, parsed, config):
  if type(node) in (str, unicode):
    return node
  content = node.get("content", "")
  if type(content) is list:
    content = "".join(_render_node(n, parsed, config) for n in content)
  return content

def _render_citation(node, parsed, config):
  doc = node.get("doc", "")
  par = node.get("par", "")
  text = _render_content(node, parsed, config)
  if doc:
    url = "%s.pdf#%d" % (doc, par)
  else:
    url = "#%d" % par

  template = tmpl_env.get_template("citation.tex")
  content = template.render({
    "doc":  doc,
    "num":  str(par),
    "url":  url,
    "text": text})
  return content

def _render_external_citation(node, parsed, config):
  ref = node.get("ref", "")
  text = _render_content(node, parsed, config)

  return "%s (%s)" % (text, ref)

def _render_term(node, parsed, config):
  doc = node.get("doc", "")
  par = node.get("par", "")
  text = _render_content(node, parsed, config)
  if doc:
    url = "%s.pdf#%d" % (doc, par)
  else:
    url = "#%d" % par

  template = tmpl_env.get_template("term.tex")
  content = template.render({
    "doc":  doc,
    "num":  str(par),
    "url":  url,
    "text": text})
  return content

def _render_formula(node, parsed, config):
  return "\\[%s\\]" % _render_content(node, parsed, config)

def _render_ord_list(node, parsed, config):
  content = _render_content(node, parsed, config)
  return "\\begin{enumerate}%s\end{enumerate}" % content

def _render_unord_list(node, parsed, config):
  content = _render_content(node, parsed, config)
  return "\\begin{itemize}%s\\end{itemize}" % content

def _render_list_item(node, parsed, config):
  content = _render_content(node, parsed, config)
  return "\\item %s\n" % content

def _render_subscript(node, parsed, config):
  return "\\textsubscript{%s}" % _render_content(node, parsed, config)

def _render_superscript(node, parsed, config):
  return "\\textsuperscript{%s}</sup>" % _render_content(node, parsed, config)

def _render_node(node, parsed, config):
  if type(node) in (str, unicode):
    return node
  content = _render_content(node, parsed, config)

  if node.get("type") in BLOCK_TAGS:
    template = tmpl_env.get_template("block.tex")
    return template.render({"block": dict_merge(node, {"content": content})})
  if node.get("type") == "paragraph":
    return "%s\n" % content
  if node.get("type") == "bold":
    return "\\textbf{%s}" % content
  if node.get("type") == "italic":
    return "\\emph{%s}" % content
  if node.get("type") == "definition":
    return "\\emph{%s}" % content
  if node.get("type") == "citation":
    return _render_citation(node, parsed, config)
  if node.get("type") == "term":
    return _render_term(node, parsed, config)
  if node.get("type") == "formula":
    return _render_formula(node, parsed, config)
  if node.get("type") == "ord_list":
    return _render_ord_list(node, parsed, config)
  if node.get("type") == "unord_list":
    return _render_unord_list(node, parsed, config)
  if node.get("type") == "list_item":
    return _render_list_item(node, parsed, config)
  if node.get("type") == "subscript":
    return _render_subscript(node, parsed, config)
  if node.get("type") == "superscript":
    return _render_superscript(node, parsed, config)
  return content

def _render_par(par, parsed, config):
  return "".join(_render_node(n, parsed, config)
    for n in par.get("content"))

def render(parsed, config):
  config = dict_merge({"src_base_url": ""}, config)
  base = config["src_base_url"]
  if base and not base.endswith("/"):
    config["src_base_url"] = base + "/"
  template = tmpl_env.get_template("template.tex")
  tex = template.render({
    "title":  parsed["title"],
    "author": parsed["author"],
    "macros": parsed["macros"].items(),
    "pars":   [dict_merge(p, {"content": _render_par(p, parsed, config)})
                for p in parsed["body"]["pars"]]})
  return tex
