import os.path
import tempfile
from contextlib import contextmanager

import pygit2
import toml
from git import Git, Repo

from django.conf import settings


@contextmanager
def gitpython_env():
    git_privkey = settings.WAGTAILLOCALIZE_PONTOON_GIT_SSH_PRIVATE_KEY

    with tempfile.NamedTemporaryFile() as privkey_file:
        privkey_file.write(git_privkey)
        privkey_file.flush()

        yield {
            'GIT_SSH_COMMAND': f'ssh -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -i {privkey_file.name}',
        }


class Repository:
    def __init__(self, pygit, gitpython):
        self.pygit = pygit
        self.gitpython = gitpython

    @classmethod
    def open(cls):
        git_clone_dir = settings.WAGTAILLOCALIZE_PONTOON_GIT_CLONE_DIR

        if not os.path.isdir(git_clone_dir):
            git_url = settings.WAGTAILLOCALIZE_PONTOON_GIT_URL

            with gitpython_env() as env:
                Repo.clone_from(
                    git_url,
                    git_clone_dir,
                    bare=True,
                    env=env,
                )

        return cls(pygit2.Repository(git_clone_dir), Repo(git_clone_dir))

    def reader(self):
        return RepositoryReader(self.pygit)

    def writer(self):
        return RepositoryWriter(self.pygit)

    def pull(self):
        with gitpython_env() as env:
            with self.gitpython.git.custom_environment(**env):
                self.gitpython.remotes.origin.fetch('+refs/heads/*:refs/remotes/origin/*')

        new_head = self.pygit.lookup_reference('refs/remotes/origin/master')
        self.pygit.head.set_target(new_head.target)

    def push(self):
        with gitpython_env() as env:
            with self.gitpython.git.custom_environment(**env):
                self.gitpython.remotes.origin.push(['refs/heads/master'])

    def get_changed_files(self, old_commit, new_commit):
        """
        For each file that has changed, yields a three-tuple containing the filename, old content and new content
        """
        if old_commit is not None and  not self.pygit.descendant_of(new_commit, old_commit):
            raise ValueError("Second commit must be a descendant of first commit")

        old_index = pygit2.Index()
        new_index = pygit2.Index()
        if old_commit is not None:
            old_tree = self.pygit.get(old_commit).tree
            old_index.read_tree(old_tree)
        else:
            old_tree = self.pygit.get('4b825dc642cb6eb9a060e54bf8d69288fbee4904')

        new_tree = self.pygit.get(new_commit).tree
        new_index.read_tree(new_tree)

        for patch in self.pygit.diff(old_tree, new_tree):
            if patch.delta.status_char() != 'M':
                continue

            if not patch.delta.new_file.path.startswith('locales/'):
                continue

            old_file_oid = old_index[patch.delta.old_file.path].oid
            new_file_oid = new_index[patch.delta.new_file.path].oid
            old_file = self.pygit.get(old_file_oid)
            new_file = self.pygit.get(new_file_oid)
            yield patch.delta.new_file.path, old_file.data, new_file.data

    def get_head_commit_id(self):
        return self.pygit.head.target.hex


class RepositoryReader:
    def __init__(self, repo):
        self.repo = repo
        self.index = pygit2.Index()
        self.last_commit = self.repo.head.target
        self.index.read_tree(self.repo.get(self.last_commit).tree)

    def read_file(self, filename):
        oid = self.index[filename].oid
        return self.repo.get(oid).data


class RepositoryWriter:
    def __init__(self, repo):
        self.repo = repo
        self.index = pygit2.Index()

    def has_changes(self):
        """
        Returns True if the contents of this writer is different to the repo's current HEAD
        """
        tree = self.repo.get(self.index.write_tree(self.repo))
        diff = tree.diff_to_tree(self.repo.get(self.repo.head.target).tree)
        return bool(diff)

    def write_file(self, filename, contents):
        """
        Inserts a file into this writer
        """
        blob = self.repo.create_blob(contents)
        self.index.add(pygit2.IndexEntry(filename, blob, pygit2.GIT_FILEMODE_BLOB))

    def write_config(self, languages, paths):
        self.write_file('l10n.toml', toml.dumps({
            'locales': languages,
            'paths': [
                {
                    'reference': str(source_path),
                    'l10n': str(locale_path),
                }
                for source_path, locale_path in paths
            ]
        }))

    def copy_unmanaged_files(self, reader):
        """
        Copies any files we don't manage from the specified reader.

        This is everything excluding l10n.toml, templates and locales.
        """
        for entry in reader.index:
            if entry.path == 'l10n.toml' or entry.path.startswith('templates/') or entry.path.startswith('locales/'):
                continue

            self.index.add(entry)

    def commit(self, message):
        """
        Creates a new commit with the contents of this writer
        """
        tree = self.index.write_tree(self.repo)

        sig = pygit2.Signature('Wagtail Localize', 'wagtail_localize_pontoon@wagtail.io')
        self.repo.create_commit('refs/heads/master', sig, sig, message, tree, [self.repo.head.target])
