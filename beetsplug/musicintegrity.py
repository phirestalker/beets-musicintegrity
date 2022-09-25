from beets.plugins import BeetsPlugin
from beets import autotag, library, ui, util, config
from beets.autotag import hooks
from beets.ui import Subcommand
import subprocess
import os
import glob
import re


class MusicIntegrityPlugin(BeetsPlugin):
    def __init__(self):
        super(MusicIntegrityPlugin, self).__init__()
        # self.import_stages = [self.on_import]
        self.config.add({
            'par2_exe': '',
            'recovery': '15',
            'memory': '1024',
            'extra_args': [],
        })
        self.write = True
        self.par2_exe = ''
        self.par2_args = []
        self.register_listener('import_begin', self.before_import)
        self.register_listener('import', self.after_import)
        self.register_listener('after_write', self.item_changed)
        self.register_listener('write', self.check_par2)
        self.register_listener('album_imported', self.on_import_album)
        self.register_listener('item_imported', self.on_import_item)
        self.register_listener('item_removed', self.file_removed)
        self.build_args()
        if not self.check_command():
            raise ui.UserError(u'cannot find par2 program. Try setting its path in the config')

    def commands(self):
        create_par_command = Subcommand('par2create', help='Create par2 sets for the tracks returned by the query')
        create_par_command.func = self.create_par2
        verify_par_command = Subcommand('par2verify', help='Verify par2 sets for the tracks returned by the query')
        verify_par_command.func = self.verify_par2
        repair_par_command = Subcommand('par2repair', help='Repair par2 sets for the tracks returned by the query')
        repair_par_command.func = self.repair_par2
        delete_par_command = Subcommand('par2delete', help='Delete par2 sets for the tracks returned by the query')
        delete_par_command.func = self.delete_par2
        return [create_par_command, verify_par_command, repair_par_command, delete_par_command]

    def create_par2(self, lib, opts, args):
        query = ui.decargs(args)
        for item in lib.items(query):
            self.process_file(item, 'create', False)

    def delete_par2(self, lib, opts, args):
        query = ui.decargs(args)
        for item in lib.items(query):
            dirname, filename, par2_filename, par2_file_path = self.get_paths(item)
            self.delete_par2_file(par2_file_path)

    def file_removed(self, item):
        dirname, filename, par2_filename, par2_file_path = self.get_paths(item)
        self.delete_par2_file(par2_file_path)

    def get_paths(self, item):
        dirname = os.path.dirname(item.path)
        filename = os.path.basename(item.path)
        par2_filename = self.get_par2_filename(filename)
        par2_file_path = os.path.join(dirname, par2_filename)
        return dirname, filename, par2_filename, par2_file_path

    def check_par2(self, item, path, tags):
        output = self.process_file(item, 'repair', False)
        if output and output.returncode != 0:
            raise library.FileOperationError(item.path, 'file could not be repaired: ' + output.stderr)

    def process_file(self, item, action, delete_par2_files):
        dirname, filename, par2_filename, par2_file_path = self.get_paths(item)

        command_line = [self.par2_exe, action]
        if action == 'create':
            command_line += self.par2_args
        command_line += [par2_file_path] if action == 'create' else [u'-q', par2_file_path + b'.par2']
        if action == 'create':
            command_line += [item.path]

        if os.path.isfile(par2_file_path + b'.par2') and delete_par2_files and action == 'create':
            self.delete_par2_file(par2_file_path)
        output = {}
        if action == 'create' or os.path.isfile(par2_file_path + b'.par2'):
            output = subprocess.run(command_line,
                stderr=subprocess.PIPE, stdout=subprocess.PIPE, universal_newlines=True)
            if output.returncode != 0:
                self._log.error(u'par2 command returned with errors: {0}.\nFor file: {1}', output.stderr, item.path)
            self._log.debug('{0} par2 output: {1}', item.path, output.stdout)
        return output

    def verify_par2(self, lib, opts, args):
        query = ui.decargs(args)
        for item in lib.items(query):
            output = self.process_file(item, 'verify', False)
            if output.returncode != 0:
                self.process_file(itme, 'repair', False)

    def repair_par2(self, lib, opts, args):
        query = ui.decargs(args)
        for item in lib.items(query):
            self.process_file(item, 'repair', False)

    # disable after_write event action during import operations
    def before_import(self, session):
        self.write = False

    # re-enable after_write event action after import finishes
    def after_import(self, lib, paths):
        self.write = True

    def on_import_album(self, lib, album):
        for item in album.items():
            self.process_file(item, 'create', True)

    def on_import_item(self, lib, item):
        self.process_file(item, 'create', True)

    def item_changed(self, item):
        if not self.write:
            return
        self.check_par2(item, "", "")
        self.process_file(item, 'create', True)

    # make sure the par2 command can be found
    def check_command(self):
        output = subprocess.run([self.par2_exe, u'--version'],
                stderr=subprocess.PIPE, stdout=subprocess.PIPE, universal_newlines=True)
        if output.returncode != 0:
            self._log.error(u'par2 command returned with errors: {0}', output.stderr)
            return False
        return True

    # prepare command arguments for par2 execution
    def build_args(self):
        self.par2_exe = (self.config['par2_exe'] or u'par2')
        self.par2_args = [u'-r' + self.config['recovery'].as_str(),
                        u'-m' + self.config['memory'].as_str(), u'-q']
        if self.config['extra_args']:
            self.par2_args += self.config['extra_args'].as_str_seq()

    def get_par2_filename(self, filename):
        return re.sub(b'[*?]', b'', os.path.splitext(filename)[0])

    def delete_par2_file(self, par2_filename):
        file_list = glob.glob(par2_filename.decode('utf-8') + u'*.par2')
        for file_path in file_list:
            try:
                os.remove(file_path)
                self._log.debug(u'removed old par file: {0}', file_path)
            except:
                self._log.error(u'could not remove file {0}', file_path)
