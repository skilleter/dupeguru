# -*- coding: utf-8 -*-
# Created By: Virgil Dupras
# Created On: 2009-12-30
# Copyright 2010 Hardcoded Software (http://www.hardcoded.net)
# 
# This software is licensed under the "BSD" License as described in the "LICENSE" file, 
# which should be included with this package. The terms are also available at 
# http://www.hardcoded.net/licenses/bsd_license

import sys
import os
import os.path as op
import compileall
import shutil
import importlib
import json

from hscommon.build import (build_dmg, add_to_pythonpath, print_and_do, copy_packages,
    build_debian_changelog, copy_qt_plugins)

def package_cocoa(edition):
    app_path = {
        'se': 'cocoa/se/build/release/dupeGuru.app',
        'me': 'cocoa/me/build/release/dupeGuru ME.app',
        'pe': 'cocoa/pe/build/release/dupeGuru PE.app',
    }[edition]
    build_dmg(app_path, '.')

def package_windows(edition, dev):
    if sys.platform != "win32":
        print("Qt packaging only works under Windows.")
        return
    add_to_pythonpath('.')
    modname = 'qt.{0}.app'.format(edition)
    appmod = importlib.import_module(modname)
    DupeGuru = appmod.DupeGuru
    distdir = 'dist'
    
    if op.exists(distdir):
        shutil.rmtree(distdir)
    
    cmd = 'cxfreeze --base-name Win32GUI --target-dir "{0}" --target-name "{1}.exe" --icon {2} run.py'
    target_name = {'se': 'dupeGuru', 'me': 'dupeGuru ME', 'pe': 'dupeGuru PE'}[edition]
    icon_path = 'images\\dg{0}_logo.ico'.format(edition)
    print_and_do(cmd.format(distdir, target_name, icon_path))
    
    if not dev:
        # Copy qt plugins
        plugin_dest = op.join(distdir, 'qt4_plugins')
        plugin_names = ['accessible', 'codecs', 'iconengines', 'imageformats']
        copy_qt_plugins(plugin_names, plugin_dest)
        
        # Compress with UPX 
        libs = [name for name in os.listdir(distdir) if op.splitext(name)[1] in ('.pyd', '.dll', '.exe')]
        for lib in libs:
            print_and_do("upx --best \"{0}\"".format(op.join(distdir, lib)))
    
    help_basedir = 'help_{0}'.format(edition)
    help_dir = 'dupeguru_{0}_help'.format(edition) if edition != 'se' else 'dupeguru_help'
    help_path = op.join(help_basedir, help_dir)
    print("Copying {0} to dist\\help".format(help_path))
    shutil.copytree(help_path, op.join(distdir, 'help'))

    # AdvancedInstaller.com has to be in your PATH
    # this is so we don'a have to re-commit installer.aip at every version change
    installer_path = op.join('qt', edition, 'installer.aip')
    shutil.copy(installer_path, 'installer_tmp.aip')
    print_and_do('AdvancedInstaller.com /edit installer_tmp.aip /SetVersion %s' % DupeGuru.VERSION)
    print_and_do('AdvancedInstaller.com /build installer_tmp.aip -force')
    os.remove('installer_tmp.aip')
    if op.exists('installer_tmp.back.aip'):
        os.remove('installer_tmp.back.aip')

def package_debian(edition):
    modname = 'qt.{0}.app'.format(edition)
    appmod = importlib.import_module(modname)
    DupeGuru = appmod.DupeGuru
    
    if op.exists('build'):
        shutil.rmtree('build')
    ed = lambda s: s.format(edition)
    destpath = op.join('build', 'dupeguru-{0}-{1}'.format(edition, DupeGuru.VERSION))
    srcpath = op.join(destpath, 'src')
    help_src = ed('help_{0}')
    os.makedirs(destpath)
    os.makedirs(srcpath)
    shutil.copy('run.py', op.join(srcpath, 'run.py'))
    packages = ['hscommon', 'core', ed('core_{0}'), 'qtlib', 'qt', 'send2trash', 'jobprogress']
    if edition == 'me':
        packages.append('hsaudiotag')
    copy_packages(packages, srcpath)
    import sip, PyQt4
    shutil.copy(sip.__file__, srcpath)
    qtsrcpath = op.dirname(PyQt4.__file__)
    qtdestpath = op.join(srcpath, 'PyQt4')
    os.makedirs(qtdestpath)
    shutil.copy(op.join(qtsrcpath, '__init__.py'), qtdestpath)
    shutil.copy(op.join(qtsrcpath, 'Qt.so'), qtdestpath)
    shutil.copy(op.join(qtsrcpath, 'QtCore.so'), qtdestpath)
    shutil.copy(op.join(qtsrcpath, 'QtGui.so'), qtdestpath)
    shutil.copytree(ed('debian_{0}'), op.join(destpath, 'debian'))
    changelogpath = op.join(help_src, 'CHANGELOG')
    changelog_dest = op.join(destpath, 'debian', 'changelog')
    project_name = ed('dupeguru-{0}')
    from_version = {'se': '2.9.2', 'me': '5.7.2', 'pe': '1.8.5'}[edition]
    build_debian_changelog(changelogpath, changelog_dest, project_name, from_version=from_version)
    help_name = {'se': 'dupeguru_help', 'me': 'dupeguru_me_help', 'pe': 'dupeguru_pe_help'}[edition]
    shutil.copytree(op.join(help_src, help_name), op.join(srcpath, 'help'))
    shutil.copy(op.join('images', ed('dg{0}_logo_128.png')), srcpath)
    compileall.compile_dir(srcpath)
    os.chdir(destpath)
    os.system("dpkg-buildpackage")

def main():
    conf = json.load(open('conf.json'))
    edition = conf['edition']
    ui = conf['ui']
    dev = conf['dev']
    print("Packaging dupeGuru {0} with UI {1}".format(edition.upper(), ui))
    if ui == 'cocoa':
        package_cocoa(edition)
    elif ui == 'qt':
        if sys.platform == "win32":
            package_windows(edition, dev)
        elif sys.platform == "linux2":
            package_debian(edition)
        else:
            print("Qt packaging only works under Windows or Linux.")

if __name__ == '__main__':
    main()
