#!/usr/bin/python
# -*- coding: utf-8 -*-

import os
import re
import sys
import getopt
import fnmatch
import time

# Class for terminal Color
class tcolor:
    DEFAULT = "\033[0m"
    BOLD = "\033[1m"
    RED = "\033[91m"
    GREEN = "\033[92m"
    BLUE = "\033[96m"
    ORANGE = "\033[93m"
    MAGENTA = "\033[95m"
    RESET = "\033[2J\033[H"
    BELL = "\a"

# Search all local repositories from current directory
def searchRepositories(dir=None):

    curdir = os.path.abspath(os.getcwd()) if dir is None else dir
    repo = []
    rsearch = re.compile(r'^/?(.*?)/\.git')
    for root, dirnames, filenames in os.walk(curdir):
        for dirnames in fnmatch.filter(dirnames, '*.git'):
            fdir = os.path.join(root, dirnames)
            fdir = fdir.replace(curdir, '')
            m = rsearch.match(fdir)
            if m:
                repo.append(os.path.join(curdir, m.group(1)))

    return repo


def terselist(repolist, behind=False, ignoreBranch=r'^$'):
    gsearch = re.compile(r'^.?([A-Z]) (.*)')
  
    uncommited = []
    repo_ahead = []
    for repo in repolist:
        branch = getDefaultBranch(repo)
        if re.match(ignoreBranch, branch):
            continue
        if len(getLocalFilesChange(repo)) > 0:
            uncommited.append(os.path.basename(repo))
            continue
        for r in getRemoteRepositories(repo):
            if len(getLocalToPush(repo, r, branch)) > 0:
                repo_ahead.append(os.path.basename(repo))
                continue
    if len(uncommited) > 0:
        print ("\033[91m=Local Changes=\033[0m")
        #print ("-------------")
        print "\n".join(uncommited)
    if len(repo_ahead) > 0:
        print ("\n=Repos Ahead=")
        #print ("-------------")
        print "\n".join(repo_ahead)


# Check state of a git repository
def checkRepository(rep, verbose=False, ignoreBranch=r'^$'):
    aitem = []
    mitem = []
    ditem = []
    gsearch = re.compile(r'^.?([A-Z]) (.*)')

    branch = getDefaultBranch(rep)
    if re.match(ignoreBranch, branch):
        return False

    changes = getLocalFilesChange(rep)
    ischange = len(changes) > 0
    actionNeeded = False # actionNeeded is branch push/pull, not local file change.

    branch = getDefaultBranch(rep)
    topush = ""
    topull = ""
    if branch != "":
        remotes = getRemoteRepositories(rep)
        for r in remotes:
            count = len(getLocalToPush(rep, r, branch))
            ischange = ischange or (count > 0)
            actionNeeded = actionNeeded or (count > 0)
            if count > 0:
                topush += " %s%s%s[%sTo Push:%s%s]" % (
                    tcolor.ORANGE,
                    r,
                    tcolor.DEFAULT,
                    tcolor.BLUE,
                    tcolor.DEFAULT,
                    count
                )

        for r in remotes:
            count = len(getRemoteToPull(rep, r, branch))
            ischange = ischange or (count > 0)
            actionNeeded = actionNeeded or (count > 0)
            if count > 0:
                topull += " %s%s%s[%sTo Pull:%s%s]" % (
                    tcolor.ORANGE,
                    r,
                    tcolor.DEFAULT,
                    tcolor.BLUE,
                    tcolor.DEFAULT,
                    count
                )

    if ischange:
        color = tcolor.BOLD + tcolor.RED
    else:
        color = tcolor.DEFAULT + tcolor.GREEN

    # Print result
    prjname = "%s%s%s" % (color, rep, tcolor.DEFAULT)
    if len(changes) > 0:
        strlocal = "%sLocal%s[" % (tcolor.ORANGE, tcolor.DEFAULT)
        strlocal += "%sTo Commit:%s%s" % (
            tcolor.BLUE,
            tcolor.DEFAULT,
            len(getLocalFilesChange(rep))
        )

        strlocal += "]"
    else:
        strlocal = ""

    print("%(prjname)s/%(branch)s %(strlocal)s%(topush)s%(topull)s" % locals())
    if verbose:
        if ischange > 0:
            filename = "  |--Local"
            print(filename)
            for c in changes:
                filename = "     |--%s%s%s" % (
                    tcolor.ORANGE,
                    c[1],
                    tcolor.DEFAULT)
                print(filename)

        if branch != "":
            remotes = getRemoteRepositories(rep)
            for r in remotes:
                commits = getLocalToPush(rep, r, branch)
                if len(commits) > 0:
                    rname = "  |--%(r)s" % locals()
                    print(rname)
                    for commit in commits:
                        commit = "     |--%s[To Push]%s %s%s%s" % (
                            tcolor.MAGENTA,
                            tcolor.DEFAULT,
                            tcolor.BLUE,
                            commit,
                            tcolor.DEFAULT)
                        print(commit)

        if branch != "":
            remotes = getRemoteRepositories(rep)
            for r in remotes:
                commits = getRemoteToPull(rep, r, branch)
                if len(commits) > 0:
                    rname = "  |--%(r)s" % locals()
                    print(rname)
                    for commit in commits:
                        commit = "     |--%s[To Pull]%s %s%s%s" % (
                            tcolor.MAGENTA,
                            tcolor.DEFAULT,
                            tcolor.BLUE,
                            commit,
                            tcolor.DEFAULT)
                        print(commit)

    return actionNeeded

def getLocalFilesChange(rep):
    files = []
    #curdir = os.path.abspath(os.getcwd())
    snbchange = re.compile(r'^(.{2}) (.*)')
    result = gitExec(rep, "git status -suno"
                     % locals())

    lines = result.split('\n')
    for l in lines:
        m = snbchange.match(l)
        if m:
            files.append([m.group(1), m.group(2)])

    return files


def hasRemoteBranch(rep, remote, branch):
    result = gitExec(rep, "git branch -r | grep '%(remote)s/%(branch)s'"
                     % locals())
    return (result != "")


def getLocalToPush(rep, remote, branch):
    if not hasRemoteBranch(rep, remote, branch):
        return []
    result = gitExec(rep, "git log %(remote)s/%(branch)s..HEAD --oneline"
                     % locals())

    return [x for x in result.split('\n') if x]


def getRemoteToPull(rep, remote, branch):
    if not hasRemoteBranch(rep, remote, branch):
        return []
    result = gitExec(rep, "git log HEAD..%(remote)s/%(branch)s --oneline"
                     % locals())

    return [x for x in result.split('\n') if x]


def updateRemote(rep):
    gitExec(rep, "git remote update")


# Get Default branch for repository
def getDefaultBranch(rep):
    sbranch = re.compile(r'^\* (.*)')
    gitbranch = gitExec(rep, "git branch | grep '*'"
                        % locals())

    branch = ""
    m = sbranch.match(gitbranch)
    if m:
        branch = m.group(1)

    return branch


def getRemoteRepositories(rep):
    result = gitExec(rep, "git remote"
                     % locals())

    remotes = [x for x in result.split('\n') if x]
    return remotes


# Custom git command
def gitExec(rep, command):
    cmd = "cd %(rep)s ; %(command)s" % locals()
    cmd = os.popen(cmd)
    return cmd.read()


# Check all git repositories
def gitcheck(verbose, checkremote, ignoreBranch, bellOnActionNeeded, shouldClear, searchDir):
    repo = searchRepositories(searchDir)
    actionNeeded = False

    if checkremote:
        print ("Please waiting, refresh the remote repositories datas")
        for r in repo:
            updateRemote(r)

    if shouldClear:
        print(tcolor.RESET)

    terselist(repo)
    return
        
    for r in repo:
        if checkRepository(r, verbose, ignoreBranch):
            actionNeeded = True

    if actionNeeded and bellOnActionNeeded:
        print(tcolor.BELL)


def usage():
    print("Usage: %s [OPTIONS]" % (sys.argv[0]))
    print("Check multiple git repository in one pass")
    print("== Common options ==")
    print("  -v, --verbose                 Show files & commits")
    print("  -r, --remote                  force remote update(slow)")
    print("  -b, --bell                    bell on action needed")
    print("  -w <sec>, --watch <sec>       after displaying, wait <sec> and run again")
    print("  -i <re>, --ignore-branch <re> ignore branches matching the regex <re>")
    print("  -d <dir>,                     Search <dir> for repositories")


def main():
    try:
        opts, args = getopt.getopt(
            sys.argv[1:],
            "vhrbw:i:d:",
            ["verbose", "help", "remote", "bell", "watch:", "ignore-branch:",
             "dir:"])
    except getopt.GetoptError, e:
        if e.opt == 'w' and 'requires argument' in e.msg:
            print "Please indicate nb seconds for refresh ex: gitcheck -w10"
        sys.exit(2)

    verbose = False
    checkremote = False
    watchInterval = 0
    bellOnActionNeeded = False
    searchDir = None
    ignoreBranch = r'^$'  # empty string
    for opt, arg in opts:
        if opt in ("-v", "--verbose"):
            verbose = True
        if opt in ("-r", "--remote"):
            checkremote = True
        if opt in ("-r", "--remote"):
            checkremote = True
        if opt in ("-b", "--bell"):
            bellOnActionNeeded = True
        if opt in ("-w", "--watch"):
            watchInterval = arg
        if opt in ("-i", "--ignore-branch"):
            ignoreBranch = arg
        if opt in ("-d", "--dir"):
            searchDir = arg
            
        if opt in ("-h", "--help"):
            usage()
            sys.exit(0)

    while True:
        gitcheck(
            verbose,
            checkremote,
            ignoreBranch,
            bellOnActionNeeded,
            watchInterval > 0,
            searchDir
        )
        if watchInterval:
            time.sleep(float(watchInterval))
        else:
            break

if __name__ == "__main__":
    main()
