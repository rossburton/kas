"""
    This plugin implements the ``kas run`` command.
"""

import logging
import subprocess
import tempfile
import os
import sys

from kas.context import create_global_context
from kas.config import Config
from kas.libcmds import Macro, Command

__license__ = 'MIT'
__copyright__ = 'Copyright (c) Arm Ltd, 2020'

# Extend the schema
import kas.configschema
kas.configschema.CONFIGSCHEMA['properties']['run'] = {"type": "string"}

class Run:
    """
    Implements a kas plugin that runs a script within the kas environment.
    """

    name = 'run'
    helpmsg = 'Run a script in the build environment.'

    @classmethod
    def setup_parser(cls, parser):
        pass

    def run(self, args):
        ctx = create_global_context(args)
        ctx.config = Config(args.config)

        macro = Macro()
        macro.add(RunCommand())
        macro.run(ctx)


class RunCommand(Command):

    def __str__(self):
        return 'run'

    def execute(self, ctx):
        with tempfile.NamedTemporaryFile(mode="wt", prefix="kas-run-") as script:
            # Write the script to a temporary file
            os.chmod(script.name, 0o700)
            # TODO if first line is #! then use that instead
            shell = ctx.environ.get('SHELL', '/bin/sh')
            script.write(f"#! {shell}\n")
            script.write(ctx.config._config["run"])
            script.file.close()

            # Export the repository locations so the script can use them
            env = ctx.environ.copy()
            for repo in ctx.config.get_repos():
                shellname = repo.name.upper().replace("-", "_")
                env[f"KAS_REPO_{shellname}_NAME"] = repo.name
                env[f"KAS_REPO_{shellname}_PATH"] = repo.path
                env[f"KAS_REPO_{shellname}_URL"] = repo.url or ""
                env[f"KAS_REPO_{shellname}_REFSPEC"] = repo.refspec or ""

            # Run the script
            ret = subprocess.call(script.name, env=env, cwd=ctx.build_dir)
            if ret != 0:
                logging.error('Script returned non-zero exit status %d', ret)
                sys.exit(ret)


__KAS_PLUGINS__ = [Run]
