# mrls

Wrapper for `mr` multiple repository tool to handle groups and symlinks over devices

```
mrls - Wrapper for `mr` multiple repository tool
https://myrepos.branchable.com/

Summary

mrls - list repos. by device and groups defined in /.mrconfig
mrls myGroup - list repos in myGroup
mrls myGroup staus - run mr status on each member of myGroup

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
```
