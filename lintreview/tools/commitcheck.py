from lintreview.tools import Tool
from lintreview.review import IssueComment
import logging
import re
import requests


log = logging.getLogger(__name__)
NOT_FOUND = 1
BAD_URL_CHECK = 2


class Commitcheck(Tool):

    name = 'commitcheck'
    good_urls = []

    def check_dependencies(self):
        """
        No dependencies.
        """
        return True

    def execute_commits(self, commits):
        """
        Check all the commit messages in the set for the pattern
        defined in the config file.
        """
        pattern = self.options.get('pattern').strip("'")

        if not pattern:
            return log.warning('Commit pattern is empty, skipping.')
        try:
            pattern = re.compile(pattern)
        except:
            return log.warning('Commit pattern is invalid, skipping.')

        bad = []
        self.good_urls = []
        for commit in commits:
            bad.append(self._check_commit(pattern, commit))
        bad = filter(None, bad)

        if not bad:
            return log.debug('No bad commit messages.')

        not_found = filter(lambda x: x[0] == NOT_FOUND, bad)
        bad_url = filter(lambda x: x[0] == BAD_URL_CHECK, bad)
        body = self.options.get('message', 'The following commits had issues.')\
            + '\n'
        if len(not_found):
            body = body + 'The pattern %s was not found in:\n' % (
                self.options['pattern'], )
            for commit in not_found:
                body += "* %s\n" % (commit[1], )
        if len(bad_url):
            body = body + 'These commits did not return a 200 response:\n'
            for commit in bad_url:
                body += "* {1} requested {2} and got a {3} response\n".\
                    format(*commit)
        self.problems.add(IssueComment(body))

    def _check_commit(self, pattern, commit):
        check_url = self.options.get('check_url')
        match = pattern.search(commit.commit.message)
        if not match:
            return [NOT_FOUND, commit.sha]
        if check_url:
            check_url = check_url.strip("'")
            if match.groupdict() == {}:
                url = check_url.format(match.group())
            else:
                url = check_url.format(**match.groupdict())
            if (url in self.good_urls):
                log.debug('URL {} already checked as good'.format(url))
                return
            r = requests.get(url)
            if r.status_code != 200:
                return [BAD_URL_CHECK, commit.sha, url, r.status_code]
            self.good_urls.append(url)
