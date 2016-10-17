# -*- coding: utf-8 -*-

# Copyright © 2012-2016 Roberto Alsina and others.

# Permission is hereby granted, free of charge, to any
# person obtaining a copy of this software and associated
# documentation files (the "Software"), to deal in the
# Software without restriction, including without limitation
# the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the
# Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice
# shall be included in all copies or substantial portions of
# the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY
# KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE
# WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR
# PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS
# OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR
# OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR
# OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
# SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""Nikola plugin categories."""

from __future__ import absolute_import
import sys
import os
import re
import io

from yapsy.IPlugin import IPlugin
from doit.cmd_base import Command as DoitCommand

from .utils import LOGGER, first_line

__all__ = (
    'Command',
    'LateTask',
    'PageCompiler',
    'RestExtension',
    'MarkdownExtension',
    'Task',
    'TaskMultiplier',
    'TemplateSystem',
    'SignalHandler',
    'ConfigPlugin',
    'PostScanner',
    'Taxonomy',
)


class BasePlugin(IPlugin):
    """Base plugin class."""

    def set_site(self, site):
        """Set site, which is a Nikola instance."""
        self.site = site
        self.inject_templates()

    def inject_templates(self):
        """Inject 'templates/<engine>' (if exists) very early in the theme chain."""
        try:
            # Sorry, found no other way to get this
            mod_path = sys.modules[self.__class__.__module__].__file__
            mod_dir = os.path.dirname(mod_path)
            tmpl_dir = os.path.join(
                mod_dir, 'templates', self.site.template_system.name
            )
            if os.path.isdir(tmpl_dir):
                # Inject tmpl_dir low in the theme chain
                self.site.template_system.inject_directory(tmpl_dir)
        except AttributeError:
            # In some cases, __builtin__ becomes the module of a plugin.
            # We couldn’t reproduce that, and really find the reason for this,
            # so let’s just ignore it and be done with it.
            pass

    def inject_dependency(self, target, dependency):
        """Add 'dependency' to the target task's task_deps."""
        self.site.injected_deps[target].append(dependency)

    def get_deps(self, filename):
        """Find the dependencies for a file."""
        return []


class PostScanner(BasePlugin):
    """The scan method of these plugins is called by Nikola.scan_posts."""

    def scan(self):
        """Create a list of posts from some source. Returns a list of Post objects."""
        raise NotImplementedError()


class Command(BasePlugin, DoitCommand):
    """Doit command implementation."""

    name = "dummy_command"

    doc_purpose = "A short explanation."
    doc_usage = ""
    doc_description = None  # None value will completely omit line from doc
    # see http://python-doit.sourceforge.net/cmd_run.html#parameters
    cmd_options = ()
    needs_config = True

    def __init__(self, *args, **kwargs):
        """Initialize a command."""
        BasePlugin.__init__(self, *args, **kwargs)
        DoitCommand.__init__(self)

    def __call__(self, config=None, **kwargs):
        """Reset doit arguments (workaround)."""
        self._doitargs = kwargs
        DoitCommand.__init__(self, config, **kwargs)
        return self

    def execute(self, options=None, args=None):
        """Check if the command can run in the current environment, fail if needed, or call _execute."""
        options = options or {}
        args = args or []

        if self.needs_config and not self.site.configured:
            LOGGER.error("This command needs to run inside an existing Nikola site.")
            return False
        return self._execute(options, args)

    def _execute(self, options, args):
        """Do whatever this command does.

        @param options (dict) with values from cmd_options
        @param args (list) list of positional arguments
        """
        raise NotImplementedError()


def help(self):
    """Return help text for a command."""
    text = []
    text.append("Purpose: %s" % self.doc_purpose)
    text.append("Usage:   nikola %s %s" % (self.name, self.doc_usage))
    text.append('')

    text.append("Options:")
    for opt in self.cmdparser.options:
        text.extend(opt.help_doc())

    if self.doc_description is not None:
        text.append("")
        text.append("Description:")
        text.append(self.doc_description)
    return "\n".join(text)

DoitCommand.help = help


class BaseTask(BasePlugin):
    """Base for task generators."""

    name = "dummy_task"

    # default tasks are executed by default.
    # the others have to be specifie in the command line.
    is_default = True

    def gen_tasks(self):
        """Generate tasks."""
        raise NotImplementedError()

    def group_task(self):
        """Return dict for group task."""
        return {
            'basename': self.name,
            'name': None,
            'doc': first_line(self.__doc__),
        }


class Task(BaseTask):
    """Task generator."""

    name = "dummy_task"


class LateTask(BaseTask):
    """Late task generator (plugin executed after all Task plugins)."""

    name = "dummy_latetask"


class TemplateSystem(BasePlugin):
    """Provide support for templating systems."""

    name = "dummy_templates"

    def set_directories(self, directories, cache_folder):
        """Set the list of folders where templates are located and cache."""
        raise NotImplementedError()

    def template_deps(self, template_name):
        """Return filenames which are dependencies for a template."""
        raise NotImplementedError()

    def get_deps(self, filename):
        """Return paths to dependencies for the template loaded from filename."""
        raise NotImplementedError()

    def get_string_deps(self, text):
        """Find dependencies for a template string."""
        raise NotImplementedError()

    def render_template(self, template_name, output_name, context):
        """Render template to a file using context.

        This must save the data to output_name *and* return it
        so that the caller may do additional processing.
        """
        raise NotImplementedError()

    def render_template_to_string(self, template, context):
        """Render template to a string using context."""
        raise NotImplementedError()

    def inject_directory(self, directory):
        """Inject the directory with the lowest priority in the template search mechanism."""
        raise NotImplementedError()

    def get_template_path(self, template_name):
        """Get the path to a template or return None."""
        raise NotImplementedError()


class TaskMultiplier(BasePlugin):
    """Take a task and return *more* tasks."""

    name = "dummy multiplier"

    def process(self, task):
        """Examine task and create more tasks. Returns extra tasks only."""
        return []


class PageCompiler(BasePlugin):
    """Compile text files into HTML."""

    name = "dummy_compiler"
    friendly_name = ''
    demote_headers = False
    supports_onefile = True
    default_metadata = {
        'title': '',
        'slug': '',
        'date': '',
        'tags': '',
        'category': '',
        'link': '',
        'description': '',
        'type': 'text',
    }
    config_dependencies = []

    def _read_extra_deps(self, post):
        """Read contents of .dep file and return them as a list."""
        dep_path = post.base_path + '.dep'
        if os.path.isfile(dep_path):
            with io.open(dep_path, 'r+', encoding='utf8') as depf:
                deps = [l.strip() for l in depf.readlines()]
                return deps
        return []

    def register_extra_dependencies(self, post):
        """Add dependency to post object to check .dep file."""
        post.add_dependency(lambda: self._read_extra_deps(post), 'fragment')

    def compile(self, source, dest, is_two_file=True, post=None, lang=None):
        """Compile the source file into HTML and save as dest."""
        # For backwards compatibility, call `compile_html`
        # If you are implementing a compiler, please implement `compile` and
        # ignore `compile_html`
        self.compile_html(source, dest, is_two_file)

    # TODO remove in v8
    def compile_html(self, source, dest, is_two_file=True):
        """Compile the source, save it on dest (DEPRECATED)."""
        raise NotImplementedError()

    def create_post(self, path, content=None, onefile=False, is_page=False, **kw):
        """Create post file with optional metadata."""
        raise NotImplementedError()

    def extension(self):
        """The preferred extension for the output of this compiler."""
        return ".html"

    def read_metadata(self, post, file_metadata_regexp=None, unslugify_titles=False, lang=None):
        """Read the metadata from a post, and return a metadata dict."""
        return {}

    def split_metadata(self, data):
        """Split data from metadata in the raw post content.

        This splits in the first empty line that is NOT at the beginning
        of the document.
        """
        split_result = re.split('(\n\n|\r\n\r\n)', data.lstrip(), maxsplit=1)
        if len(split_result) == 1:
            return '', split_result[0]
        # ['metadata', '\n\n', 'post content']
        return split_result[0], split_result[-1]

    def get_compiler_extensions(self):
        """Activate all the compiler extension plugins for a given compiler and return them."""
        plugins = []
        for plugin_info in self.site.compiler_extensions:
            if plugin_info.plugin_object.compiler_name == self.name:
                plugins.append(plugin_info)
        return plugins


class CompilerExtension(BasePlugin):
    """An extension for a Nikola compiler.

    If you intend to implement those in your own compiler, you can:
    (a) create a new plugin class for them; or
    (b) use this class and filter them yourself.
    If you choose (b), you should the compiler name to the .plugin
    file in the Nikola/Compiler section and filter all plugins of
    this category, getting the compiler name with:
        p.details.get('Nikola', 'Compiler')
    Note that not all compiler plugins have this option and you might
    need to catch configparser.NoOptionError exceptions.
    """

    name = "dummy_compiler_extension"
    compiler_name = "dummy_compiler"


class RestExtension(CompilerExtension):
    """Extensions for reStructuredText."""

    name = "dummy_rest_extension"
    compiler_name = "rest"


class MarkdownExtension(CompilerExtension):
    """Extensions for Markdown."""

    name = "dummy_markdown_extension"
    compiler_name = "markdown"


class SignalHandler(BasePlugin):
    """Signal handlers."""

    name = "dummy_signal_handler"


class ConfigPlugin(BasePlugin):
    """A plugin that can edit config (or modify the site) on-the-fly."""

    name = "dummy_config_plugin"


class ShortcodePlugin(BasePlugin):
    """A plugin that adds a shortcode."""

    name = "dummy_shortcode_plugin"


class Importer(Command):
    """Basic structure for importing data into Nikola.

    The flow is:

    read_data
    preprocess_data
    parse_data
    generate_base_site
        populate_context
        create_config
    filter_data
    process_data

    process_data can branch into:

    import_story (may use import_file and save_post)
    import_post (may use import_file and save_post)
    import_attachment (may use import_file)

    Finally:

    write_urlmap
    """

    name = "dummy_importer"

    def _execute(self, options={}, args=[]):
        """Import the data into Nikola."""
        raise NotImplementedError()

    def generate_base_site(self, path):
        """Create the base site."""
        raise NotImplementedError()

    def populate_context(self):
        """Use data to fill context for configuration."""
        raise NotImplementedError()

    def create_config(self):
        """Use the context to create configuration."""
        raise NotImplementedError()

    def read_data(self, source):
        """Fetch data into self.data."""
        raise NotImplementedError()

    def preprocess_data(self):
        """Modify data if needed."""
        pass

    def parse_data(self):
        """Convert self.data into self.items."""
        raise NotImplementedError()

    def filter_data(self):
        """Remove data that's not to be imported."""
        pass

    def process_data(self):
        """Go through self.items and save them."""

    def import_story(self):
        """Create a page."""
        raise NotImplementedError()

    def import_post(self):
        """Create a post."""
        raise NotImplementedError()

    def import_attachment(self):
        """Create an attachment."""
        raise NotImplementedError()

    def import_file(self):
        """Import a file."""
        raise NotImplementedError()

    def save_post(self):
        """Save a post to disk."""
        raise NotImplementedError()


class Taxonomy(BasePlugin):
    """Taxonomy for posts.

    A taxonomy plugin allows to classify posts (see #2107) by
    classification strings.
    """

    name = "dummy_taxonomy"

    # Adjust the following values in your plugin!

    # The classification name to be used for path handlers.
    classification_name = "taxonomy"
    # The classification name to be used when storing the classification
    # in the metadata. If set to None, the classification won't be stored
    # in the metadata.
    metadata_name = "taxonomy"
    # Variable for the overview page template which contains the list of
    # classifications.
    overview_page_variable_name = "taxonomy"
    # If True, there can be more than one classification per post; in that case,
    # the classification data in the metadata is stored as a list. If False,
    # the classification data in the metadata is stored as a string, or None
    # when no classification is given.
    more_than_one_classifications_per_post = False
    # Whether the classification has a hierarchy.
    has_hierarchy = False
    # If True, the list for a classification includes all posts with a
    # sub-classification (in case has_hierarchy is True).
    include_posts_from_subhierarchies = False
    # Whether to show the posts for one classification as an index or
    # as a post list.
    show_list_as_index = False
    # The template to use for the post list for one classification.
    # Set to none to avoid generating overviews.
    template_for_list_of_one_classification = "tagindex.tmpl"
    # The template to use for the classification overview page.
    template_for_classification_overview = "list.tmpl"
    # Whether this classification applies to posts.
    apply_to_posts = True
    # Whether this classification applies to pages.
    apply_to_pages = False
    # The minimum number of posts a classification must have to be listed in
    # the overview.
    minimum_post_count_per_classification_in_overview = 1
    # Whether post lists resp. indexes should be created for empty
    # classifications.
    omit_empty_classifications = False
    # Whether to include all classifications for all languages in every
    # language, or only the classifications for one language in its language's
    # pages.
    also_create_classifications_from_other_languages = True

    def is_enabled(self, lang=None):
        """Return True if this taxonomy is enabled, or False otherwise.

        If lang is None, this determins whether the classification is
        made at all. If lang is not None, this determines whether the
        overview page and the classification lists are created for this
        language.
        """
        return True

    def classify(self, post, lang):
        """Classify the given post for the given language.

        Must return a list or tuple of strings.
        """
        raise NotImplementedError()

    def sort_posts(self, posts, classification, lang):
        """Sort the given list of posts.

        The sort must happen in-place.
        """
        pass

    def sort_classifications(self, classifications, lang):
        """Sort the given list of classification strings.

        For hierarchical taxonomies, the elements of the list are a single
        path element of the path returned by extract_hierarchy().

        The sort must happen in-place.
        """
        pass

    def get_list_path(self, lang, type='page'):
        """A path handler for the list of all classifications.

        Must return a list or tuple, together with a boolean indicating
        whether INDEX_FILE should always be added (True) or not (False).

        In case INDEX_FILE should not be added, the last element in the returned
        path must have no extension, and the PRETTY_URLS config must be ignored
        by this handler. The return value will be modified based on the
        PRETTY_URLS and INDEX_FILE settings.

        Type can be either 'page', 'feed' (for Atom feed) or 'rss'.
        """
        raise NotImplementedError()

    def get_path(self, classification, lang, type='page'):
        """A path handler for the given classification.

        Must return a list or tuple, together with a boolean indicating
        whether INDEX_FILE should always be added (True) or not (False).

        In case INDEX_FILE should not be added, the last element in the returned
        path must have no extension, and the PRETTY_URLS config must be ignored
        by this handler. The return value will be modified based on the
        PRETTY_URLS and INDEX_FILE settings.

        Type can be either 'page', 'feed' (for Atom feed) or 'rss'.

        For hierarchical taxonomies, the result of extract_hierarchy is provided
        as `classification`. For non-hierarchical taxonomies, the classification
        string itself is provided as `classification`.
        """
        raise NotImplementedError()

    def extract_hierarchy(self, classification):
        """Given a classification, return a list of parts in the hierarchy.

        For non-hierarchical taxonomies, it usually suffices to return
        `[classification]`.
        """
        return [classification]

    def recombine_classification_from_hierarchy(self, hierarchy):
        """Given a list of parts in the hierarchy, return the classification string.

        For non-hierarchical taxonomies, it usually suffices to return hierarchy[0].
        """
        return hierarchy[0]

    def provide_list_context_and_uptodate(self, lang):
        """Provide data for the context and the uptodate list for the list of all classifiations.

        Must return a tuple of two dicts. The first is merged into the page's context,
        the second will be put into the uptodate list of all generated tasks.

        Context must contain `title`.
        """
        raise NotImplementedError()

    def provide_context_and_uptodate(self, classification, lang):
        """Provide data for the context and the uptodate list for the list of the given classifiation.

        Must return a tuple of two dicts. The first is merged into the page's context,
        the second will be put into the uptodate list of all generated tasks.

        Context must contain `title`, which should be something like 'Posts about <classification>',
        and `classification_title`, which should be related to the classification string.
        """
        raise NotImplementedError()

    def postprocess_posts_per_classification(self, posts_per_classification_per_language, flat_hierarchy_per_lang=None, hierarchy_lookup_per_lang=None):
        """Rearrange, modify or otherwise use the list of posts per classification and per language.

        For compatibility reasons, the list could be stored somewhere else as well.

        In case `has_hierarchy` is `True`, `flat_hierarchy_per_lang` is the flat
        hierarchy consisting of `utils.TreeNode` elements, and `hierarchy_lookup_per_lang`
        is the corresponding hierarchy lookup mapping classification strings to
        `utils.TreeNode` objects.
        """
        pass
