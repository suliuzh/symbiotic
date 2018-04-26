"""
BenchExec is a framework for reliable benchmarking.
This file is part of BenchExec.

Copyright (C) 2007-2015  Dirk Beyer
All rights reserved.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""
from os.path import dirname, abspath
from symbiotic.utils.utils import print_stdout
try:
    from symbiotic.versions import llvm_version
except ImportError:
    # the default version
    llvm_version='3.9.1'

try:
    import benchexec.util as util
    from benchexec.tools.template import BaseTool
except ImportError:
    # fall-back solution (at least for now)
    import symbiotic.benchexec.util as util
    from symbiotic.benchexec.tools.template import BaseTool

def dump_error(bindir, ismem=False):
    abd = abspath(bindir)
    if ismem:
        pth = abspath('{0}/klee-last/test000001.ptr.err'.format(abd))
    else:
        pth = abspath('{0}/klee-last/test000001.assert.err'.format(abd))

    try:
        f = open(pth, 'r')
        print('\n --- Error trace ---\n')
        for line in f:
            print_stdout(line, print_nl = False)
        print('\n --- ----------- ---')
    except OSError:
        from symbiotic.utils import dbg
        # this dumping is just for convenience,
        # so do not return any error
        dbg('Failed dumping the error')


# we use are own fork of KLEE, so do not use the official
# benchexec module for klee (FIXME: update the module so that
# we can use it)
class SymbioticTool(BaseTool):
    """
    Symbiotic tool info object
    """

    def __init__(self, opts):
        self._options = opts

    def executable(self):
        """
        Find the path to the executable file that will get executed.
        This method always needs to be overridden,
        and most implementations will look similar to this one.
        The path returned should be relative to the current directory.
        """
        return util.find_executable('klee')

    def version(self, executable):
        """
        Determine a version string for this tool, if available.
        """
        return self._version_from_tool(executable, arg='-version')

    def name(self):
        """
        Return the name of the tool, formatted for humans.
        """
        return 'klee'

    def llvm_version(self):
        """
        Return required version of LLVM
        """
        return llvm_version

    def set_environment(self, symbiotic_dir, opts):
        """
        Set environment for the tool
        """

        from os import environ

        # XXX: maybe there is a nicer solution?
        if opts.devel_mode:
            symbiotic_dir += '/install'

        if opts.is32bit:
            environ['KLEE_RUNTIME_LIBRARY_PATH'] \
                = '{0}/llvm-{1}/lib32/klee/runtime'.format(symbiotic_dir, self.llvm_version())
        else:
            environ['KLEE_RUNTIME_LIBRARY_PATH'] \
                = '{0}/llvm-{1}/lib/klee/runtime'.format(symbiotic_dir, self.llvm_version())

    def compilation_options(self):
        """
        List of compilation options specific for this tool
        """
        opts = []
        if self._options.property.undefinedness():
                opts.append('-fsanitize=undefined')
                opts.append('-fno-sanitize=unsigned-integer-overflow')
        elif self._options.property.signedoverflow():
                opts.append('-fsanitize=signed-integer-overflow')
                opts.append('-fsanitize=shift')

        return opts

    def prepare(self):
        """
        Prepare the bitcode for verification - return a list of
        LLVM passes that should be run on the code
        """
        # make all memory symbolic (if desired)
        # and then delete undefined function calls
        # and replace them by symbolic stuff
        passes = \
        ['-rename-verifier-funs',
         '-rename-verifier-funs-source={0}'.format(self._options.sources[0])]

        if self._options.property.undefinedness() or \
           self._options.property.signedoverflow():
            passes.append('-replace-ubsan')

        if not self._options.explicit_symbolic:
            passes.append('-initialize-uninitialized')

        return passes

    def describe_error(self, llvmfile):
        dump_error(dirname(llvmfile), self._options.property.memsafety())
