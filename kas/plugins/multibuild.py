# kas - setup tool for bitbake based projects
#
# Copyright (c) Siemens AG, 2017-2018
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
"""
    This plugin implements the ``kas build`` command.

    When this command is executed, kas will checkout repositories, setup the
    build environment and then invoke bitbake to build the targets selected
    in the chosen config file.

    For example, to build the configuration described in the file
    ``kas-project.yml`` you could run::

        kas build kas-project.yml
"""

import sys
import pathlib
import os
from kas.context import create_global_context
from kas.config import Config
from kas.libkas import find_program, run_cmd
from kas.libcmds import Macro, Command
from kas.plugins import build

__license__ = 'MIT'
__copyright__ = 'Copyright (c) Siemens AG, 2017-2018'


class MultiBuild:
    """
        This class implements the build plugin for kas.
    """

    name = 'multibuild'
    helpmsg = (
        'Checks out all necessary repositories and builds using bitbake as '
        'specified in the configuration file.'
    )

    @classmethod
    def setup_parser(cls, parser):
        """
            Setup the argument parser for the build plugin
        """

        parser.add_argument('extra_bitbake_args',
                            nargs='*',
                            help='Extra arguments to pass to bitbake')
        parser.add_argument('--target',
                            action='append',
                            help='Select target to build')
        parser.add_argument('-c', '--cmd', '--task', dest='task',
                            help='Select which task should be executed')

    def run(self, args):
        """
            Executes the build command of the kas plugin.
        """

        ctx = create_global_context(args)
        ctx.config = Config(args.config, args.target, args.task)

        macro = Macro()
        macro.add(GenerateMulticonfCommand())
        macro.add(build.BuildCommand(args.extra_bitbake_args))
        macro.run(ctx, args.skip)


class GenerateMulticonfCommand(Command):
    def __init__(self):
        super().__init__()

    def __str__(self):
        return 'multibuild'

    def get_search_path(self):
        paths = []
        for filename in self.context.config.filenames:
            path = os.path.dirname(filename)
            if path not in paths:
                paths.append(pathlib.Path(path))
        return paths

    def write_conf(self, name, config):
        # TODO mkdir
        filename = self.context.build_dir + f"/conf/multiconfig/{name}.conf"
        with open(filename, 'w') as fds:
            fds.write(config.get_local_conf_header())
            # Make this up and hope for the best
            fds.write(f'TMPDIR_append = "-{name}"\n')
            fds.write('MACHINE ??= "{}"\n'.format(
                config.get_machine(from_env=False)))
            fds.write('DISTRO ??= "{}"\n'.format(
                config.get_distro(from_env=False)))

    def execute(self, ctx):
        self.context = ctx
        searchpath = self.get_search_path()
        for name in ctx.config.get_multiconfig():
            configname = name + ".yml"
            # All potential filenames
            candidates = [path / configname for path in searchpath]
            # Filenames that exist
            candidates = [f for f in candidates if f.exists()]
            if not candidates:
                print(f"Cannot find {configname}")
            print(f"found {candidates[0]}")

            newconf = Config(str(candidates[0]))
            # This is nonsense
            newconf._config = newconf.handler.get_config()[0]
            # TODO: harvest targets and rewrite what we're firing? Does kas work if I just do mc:juno as shorthand for 'read the juno kas'?
            # write a config file
            self.write_conf(name, newconf)

__KAS_PLUGINS__ = [MultiBuild]
