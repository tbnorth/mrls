#!/usr/bin/env python3
"""
mrls - Wrapper for `mr` multiple repository tool
https://myrepos.branchable.com/

Summary

mrls - list repos. by device and groups defined in /.mrconfig
mrls myGroup - list repos in myGroup
mrls myGroup status - run mr status on each member of myGroup

`mr` can be confused by symlinks across devices, so `mrls` shows lines like

N=47  mr -d /mnt/edata
N=2   mr -d /mnt/usr1
snnm pypanart drifters

to show there are 47 repos. under the real path /mnt/edata, and 2 under
the real path /mnt/usr1.  Output also shows three group names.

`mrls` lists groups defined in ~/.mrconfig, a `mrls` extension to `mr`.
Groups are defined by `groups = group1 group2 ...` lines in ~/.mrconfig.

    mrls mygrp status -uno

would generate a shell command to run `mr` on only the repos. which are
members of `mygrp`.  Running under Gnu Screen, the command will be stuffed
into the command line waiting for you to hit enter.  Otherwise the command
will just be printed and you must copy / paste it to run it.

The group command will look like:

echo repo1 repo2 | tr ' ' \\n | xargs -I_GRP_ mr -d /a/path/_GRP_ status -uno

which breaks down as follows:

echo repo1 repo2
  a list of the unique parts of the path to each repo
tr ' ' \\n
  turns the list separators into newlines for xargs
-I _GRP_
  defines _GRP_ as the part of the command that will be
  substituted for each group member
/a/path/
  the common prefix path for all group members

Terry N. Brown terrynbrown@gmail.com Tue Feb 12 10:37:22 CST 2019
"""

import argparse
import os
import subprocess
import sys
from collections import defaultdict
from configparser import ConfigParser
from tempfile import mkstemp


def make_parser():
    """Generate a command parser, mostly so `mrls -h` shows help"""
    parser = argparse.ArgumentParser(
        description="""
Wrapper for `mr` multiple repository tool https://myrepos.branchable.com/

Just `mrls` to list repos. of different devices, and list groups.

`mrls <groupname> <group command>` to run command on group memebers. E.g.

    mrls mygrp status -uno

Define groups with `groups = group1 group2` lines in ~/.mrconfig.  The group
`ALL` is automatically defined as the list of all repos., spanning devices.
        """.strip(),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "group_cmd",
        nargs=argparse.REMAINDER,  # collect remaining arguments in list
        help="Command to run on group members",
        metavar="GROUP CMD",
    )
    parser.add_argument(
        "--use",
        help="Use this group for all commands implicitly. "
        "This is *persistent* until --all is used (except for `ALL`).",
        metavar="GROUP",
    )
    parser.add_argument(
        "--all", help="Reset effect of --use GROUP.", action='store_true'
    )
    return parser


def get_opt():

    opt = make_parser().parse_args()
    group_path = os.path.expanduser("~/.mrconfig_group")
    if opt.all:
        if opt.use:
            sys.stderr.write("Don't mix --use and --all\n")
            exit(10)
        elif os.path.exists(group_path):
            os.unlink(group_path)
            sys.stderr.write("Group cleared, using all repos.\n")
        else:
            sys.stderr.write("No group set, already using all repos.\n")
        if opt.group_cmd:
            sys.stderr.write(
                "\nmrls only sends commands to groups, did you mean"
                "\nmr %s\n\n" % (' '.join(opt.group_cmd))
            )
            opt.group_cmd = None
    if opt.use == 'ALL':
        opt.group_cmd = ['ALL'] + (opt.group_cmd or [])
    else:
        if opt.use:
            open(group_path, 'w').write(opt.use)
        if os.path.exists(group_path):
            group = open(group_path).read()
            sys.stderr.write(
                "\nNote: use mrls --all to stop using group '%s'\n\n" % group
            )
            opt.group_cmd = [group] + (opt.group_cmd or [])
    if opt.group_cmd and '--' in opt.group_cmd:
        opt.group_cmd.remove('--')
    return opt


def get_cmd(group, paths, common, uncommon, group_cmd):
    """build command"""
    uncommon = ' '.join((repr(i) if i else """'""'""") for i in uncommon)
    cmd = (
        r"echo {uncommon} | tr ' ' \\n | xargs -I{group} "
        "mr -d {common}{group} {cmd}".format(
            common=common,
            uncommon=uncommon,
            group="_%s_" % group.upper(),
            cmd=' '.join(group_cmd),
        )
    )
    if len(cmd) > 240:
        fd, filepath = mkstemp(suffix='.lst', prefix='mrls_')
        tmp = os.fdopen(fd, 'w')
        tmp.write("%s\n" % '\n'.join(paths))
        tmp.close()
        cmd = r"xargs <{filepath} -I{group} " "mr -d {group} {cmd}".format(
            common=common,
            uncommon=uncommon,
            group="_%s_" % group.upper(),
            cmd=' '.join(group_cmd),
            filepath=filepath,
        )
    return cmd


def main():

    opt = get_opt()
    group_cmd = opt.group_cmd

    config = ConfigParser()
    config.read(os.path.expanduser("~/.mrconfig"))

    home = os.path.expanduser("~")
    count = defaultdict(lambda: 0)  # count repos on devices
    groups = defaultdict(list)  # group to paths mapping

    for section in config.sections():
        path = os.path.join(home, section)
        fullpath = os.path.realpath(path)
        path = fullpath
        try:
            stat = os.stat(path)
            dev = stat.st_dev
            while len(path) > 1 and stat.st_dev == dev:
                parent = os.path.dirname(path)
                stat = os.stat(parent)
                if stat.st_dev == dev:
                    path = parent
        except FileNotFoundError:
            path = 'NOT_ON_THIS_SYSTEM'

        count[path] += 1

        if 'groups' in config[section]:
            for group in config[section]['groups'].split():
                groups[group].append(fullpath)
        groups['ALL'].append(fullpath)

    if group_cmd and len(group_cmd) == 1:  # just list group members
        group = group_cmd.pop(0)
        print("\n".join(groups[group]))
    elif group_cmd:  # prepare and show group shell command
        group = group_cmd.pop(0)
        paths = groups[group]
        common = os.path.commonprefix(paths)
        uncommon = [i[len(common) :] for i in paths]
        cmd = get_cmd(group, paths, common, uncommon, group_cmd)
        if os.environ.get('STY'):  # running screen, push cmd into command line
            proc = subprocess.Popen(
                ['screen', '-X', 'stuff', cmd.replace('\\', '\\\\')]
            )
            proc.communicate()
        else:
            print(cmd)
    else:  # just list devices and groups
        print("Repos. by drive:")
        for path in sorted(count):
            print("N=%s mr -d %s " % (str(count[path]).ljust(3), path))
        print("Groups: " + ' '.join(groups))


if __name__ == "__main__":
    main()
