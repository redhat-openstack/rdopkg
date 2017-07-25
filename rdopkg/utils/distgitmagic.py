import os
from rdopkg import helpers
import rdopkg.utils.cmd
from rdopkg.utils import specfile


SAMPLE_SPEC = u"""
Name:             {name}
Epoch:            1
Version:          {version}
Release:          {release}%{{?dist}}
Summary:          Amazing {name} package

Group:            Development/Languages
License:          ASL 2.0
URL:              http://pypi.python.org/pypi/%{{name}}
Source0:          http://pypi.python.org/lul/%{{name}}/%{{name}}-%{{version}}.tar.gz

BuildArch:        noarch
BuildRequires:    python-setuptools
BuildRequires:    python2-devel

Requires:         python-argparse
Requires:         python-iso8601
Requires:         python-prettytable

%description
{name} is incredibly interesting and useful to all beings in universe.

It's pretty good stuff for a testing package that doesn't even exist.

%prep
%setup -q

%build
%{{__python}} setup.py build

%install
%{{__python}} setup.py install -O1 --skip-build --root %{{buildroot}}

%files
%doc README.rst
%{{_bindir}}/{name}

%changelog
* Mon Apr 23 2017 Jakub Ruzicka <jruzicka@redhat.com> {version}-{release}
- Update to upstream {version}
- Introduce new bugs (rhbz#123456)

* Tue Mar 23 2016 Jakub Ruzicka <jruzicka@redhat.com> 1.2.2-1
- Update to upstream 1.2.2

* Tue Jun 23 2015 Jakub Ruzicka <jruzicka@redhat.com> 1.1.1-1
- Update to upstream 1.1.1
- Lorem Ipsum
- Dolor sit Amet
"""  # noqa


# silent run() by default
def run(*args, **kwargs):
    kwargs['log_cmd'] = False
    return rdopkg.utils.cmd.run(*args, **kwargs)


class SilentGit(rdopkg.utils.cmd.Git):
    def __call__(self, *args, **kwargs):
        if kwargs.get('log_cmd', None) is None:
            kwargs['log_cmd'] = False
        return super(SilentGit, self).__call__(*args, **kwargs)


# silent git() by default
git = SilentGit()


def do_patch(fn, content, msg):
    f = open(fn, 'a')
    f.write(content)
    f.close()
    git('add', fn)
    git('commit', '-m', msg)


def add_n_patches(n, patch_name='Test Patch %d',
                  branch='master-patches'):
    if branch:
        old_branch = rdopkg.utils.cmd.git.current_branch()
        git('checkout', branch)
    for i in range(1, n + 1):
        pn = patch_name % i
        do_patch(pn, pn + '\n', pn)
    if branch:
        git('checkout', old_branch)


def create_sample_distgit(name, version='1.2.3', release='1', path=None):
    if not path:
        path = name
    assert not os.path.exists(path)
    os.makedirs(path)
    with helpers.cdir(path):
        txt = SAMPLE_SPEC.format(name=name, version=version, release=release)
        spec = specfile.Spec(fn='%s.spec' % name, txt=txt)
        spec.set_tag('Name', name)
        spec.save()
        git('init',)
        git('add', '.')
        git('commit', '-m', 'Initial import', isolated=True)
    return os.path.abspath(path)


def create_sample_patches_branch(n):
    version = specfile.Spec().get_tag('Version')
    branch = rdopkg.utils.cmd.git.current_branch()
    git('tag', version, fatal=False, log_fail=False)
    git('branch', '%s-patches' % branch)
    add_n_patches(n, patch_name="Original Patch %d")


def create_sample_upstream_new_version(
        new_version, n_patches, n_from_patches_branch):
    branch = rdopkg.utils.cmd.git.current_branch()
    old_version = specfile.Spec().get_tag('Version')
    git('checkout', '-b', 'upstream', old_version)
    add_n_patches(n_patches,
                  patch_name='Upstream Commit %d',
                  branch=None)
    for i in range(n_from_patches_branch):
        # emulate upstream patches that were backported
        git('cherry-pick', 'master-patches' + i * '~')
    git('tag', new_version)
    git('checkout', branch)