__name__ = "html"

import os.path
import codecs
import tempfile
import subprocess
import hashlib
from jinja2 import Environment, PackageLoader
import wand.image, wand.color

from hypertex.constants import BLOCK_TAGS
from hypertex.util import dict_merge

tmpl_env = Environment(loader=PackageLoader("hypertex.render", "html"))

def _render_content(node, parsed, config):
  if type(node) in (str, unicode):
    return node
  content = node.get("content", "")
  if type(content) is list:
    content = "".join([_render_node(n, parsed, config) for n in content])
  return content

def _render_citation(node, parsed, config):
  doc = node.get("doc", "")
  par = node.get("par", "")
  text = _render_content(node, parsed, config)
  if doc:
    url = "%s%s.html#%d" % (config["src_base_url"], doc, par)
  else:
    url = "#%d" % par

  template = tmpl_env.get_template("citation.html")
  content = template.render({
    "doc":  doc,
    "num":  str(par),
    "url":  url,
    "text": text})
  return content

def _render_external_citation(node, parsed, config):
  text = _render_content(node, parsed, config)
  template = tmpl_env.get_template("external_citation.html")
  refid = node.get("refid")
  ref = parsed["refs"].get(refid)
  content = template.render(dict_merge(ref,
    {"node": node, "text": text}))
  return content

def _render_term(node, parsed, config):
  doc = node.get("doc", "")
  par = node.get("par", "")
  text = _render_content(node, parsed, config)
  if doc:
    url = "%s%s.html#%d" % (config["src_base_url"], doc, par)
  else:
    url = "#%d" % par

  template = tmpl_env.get_template("term.html")
  content = template.render({
    "doc":  doc,
    "num":  str(par),
    "url":  url,
    "text": text})
  return content

def _render_ord_list(node, parsed, config):
  content = _render_content(node, parsed, config)
  return "<ol>%s</ol>" % content

def _render_unord_list(node, parsed, config):
  content = _render_content(node, parsed, config)
  return "<ul>%s</ul>" % content

def _render_list_item(node, parsed, config):
  content = _render_content(node, parsed, config)
  return "<li>%s</li>" % content

def _render_formula_as_pdf(formula, macros):
  "Takes a LaTeX formula and returns a path to a PDF."
  template = tmpl_env.get_template("formula.tex")
  tex = template.render({
    "formula": formula,
    "macros":  macros.items()})
  (f, path) = tempfile.mkstemp()
  codecs.open(path, encoding="utf8", mode="w").write(tex)
  
  p = subprocess.Popen(["pdflatex",
    "-interaction=batchmode", "-output-dir=%s" % os.path.dirname(path),
    path],
    stdout=subprocess.PIPE)
  out, err = p.communicate()
  if err:
    print err
  return path + ".pdf"

def _generate_formula_filename(formula, macros):
  s = formula + repr(macros)
  return hashlib.md5(s).hexdigest() + ".png"

def _get_formula_png_path(formula, macros, img_dir):
  return "%s/%s" % (img_dir, _generate_formula_filename(formula, macros))

def _render_formula_as_image(formula, macros, img_dir):
  "Takes a LaTeX formula and returns a path to a PNG."
  pngpath = _get_formula_png_path(formula, macros, img_dir)
  if os.path.exists(pngpath):
    return pngpath

  print "Rendering formula...\n%s" % formula
  pdfpath = _render_formula_as_pdf(formula, macros)

  p = subprocess.Popen(["convert",
    "-density", "120", "-trim", "-transparent", "#FFFFFF",
    pdfpath, pngpath],
    stdout=subprocess.PIPE)
  out, err = p.communicate()
  if err:
    print err

  return pngpath

def _render_formula(node, parsed, config):
  """
  Renders a formula tag.  If it has an img attribute, it will be rendered
  with LaTeX and the result will be included as an image.
  """
  formula = _render_content(node, parsed, config)
  as_img = node.get("img")
  content = ""
  if as_img:
    if not config["img_dir"]:
      print "Error: no img_dir provided.  Skipping formula."
      return ""
    img_path = _render_formula_as_image(formula, parsed["macros"], config["img_dir"])
    if img_path:
      img_url = "%s/%s" % (config["img_base_url"], os.path.basename(img_path))
      content = "<div class=\"formula\"><img src=\"%s\" alt=\"%s\" /></div>" % (img_url, formula)
    else:
      content = "<div class=\"formula\">%s</div>" % formula
  else:
    content = "<div class=\"formula\">\[ %s \]</div>" % formula
  return content

def _render_subscript(node, parsed, config):
  return "<sub>%s</sub>" % _render_content(node, parsed, config)

def _render_superscript(node, parsed, config):
  return "<sup>%s</sup>" % _render_content(node, parsed, config)

def _render_node(node, parsed, config):
  if type(node) in (str, unicode):
    return node
  content = _render_content(node, parsed, config)
  if node.get("type") in BLOCK_TAGS:
    template = tmpl_env.get_template("block.html")
    return template.render({"block": dict_merge(node, {"content": content})})
  if node.get("type") == "paragraph":
    return "<p>%s</p>" % content
  if node.get("type") == "bold":
    return "<b>%s</b>" % content
  if node.get("type") == "italic":
    return "<i>%s</i>" % content
  if node.get("type") == "definition":
    return "<span class=\"definition\">%s</span>" % content
  if node.get("type") == "citation":
    return _render_citation(node, parsed, config)
  if node.get("type") == "term":
    return _render_term(node, parsed, config)
  if node.get("type") == "external_citation":
    return _render_external_citation(node, parsed, config)
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
  return "".join(_render_node(n, parsed, config) for n in par.get("content"))

def _escape_macros(macros):
  return [(k, v.replace("\\", "\\\\")) for (k, v) in macros.items()]

def render(parsed, config={}):
  """
  Takes a parsed hypertex file and renders it as HTML.
  Accepts a config dict which should contain img_dir and img_base_url when
  the output format is HTML.
  """
  config = dict_merge(
    {"img_dir": None, "img_base_url": "", "src_base_url": ""},
    config)
  base = config["src_base_url"]
  if base and not base.endswith("/"):
    config["src_base_url"] = base + "/"
  template = tmpl_env.get_template("template.html")
  pars = [dict_merge(p, {"content": _render_par(p, parsed, config)})
    for p in parsed["body"]["pars"]]
  html = template.render({
    "title":   parsed["title"],
    "author":  parsed["author"],
    "macros":  _escape_macros(parsed["macros"]),
    "pars":    pars,
    "refs":    parsed["refs"]})
  return html
