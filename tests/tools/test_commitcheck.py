from tests import load_fixture, create_commits
from lintreview.review import Problems
from lintreview.review import IssueComment
from lintreview.tools.commitcheck import Commitcheck
from nose.tools import eq_
from unittest import TestCase
import responses


class TestCommitCheck(TestCase):

    fixture = load_fixture('commits.json')

    def setUp(self):
        self.fixture_data = create_commits(self.fixture)
        self.problems = Problems()
        self.tool = Commitcheck(self.problems)

    def test_execute_commits__no_pattern(self):
        self.tool.options['pattern'] = ''
        self.tool.execute_commits(self.fixture_data)
        eq_(0, len(self.problems), 'Empty pattern does not find issues')

    def test_execute_commits__broken_regex(self):
        self.tool.options['pattern'] = '(.*'
        self.tool.execute_commits(self.fixture_data)
        eq_(0, len(self.problems), 'Empty pattern does not find issues')

    def test_execute_commits__match(self):
        self.tool.options['pattern'] = '\w+'
        self.tool.execute_commits(self.fixture_data)
        eq_(0, len(self.problems), 'Commits that do match are ok')

        self.tool.options['pattern'] = 'bugs?'
        self.tool.execute_commits(self.fixture_data)
        eq_(0, len(self.problems), 'Commits that do match are ok')

    def test_execute_commits__no_match(self):
        self.tool.options['pattern'] = '\d+'
        self.tool.execute_commits(self.fixture_data)
        eq_(1, len(self.problems), 'Commits that do not match cause errors')
        msg = (
            'The following commits had issues.\n'
            'The pattern \d+ was not found in:\n'
            '* 6dcb09b5b57875f334f61aebed695e2e4193db5e\n')
        expected = IssueComment(msg)
        eq_(expected, self.problems.all()[0])

    def test_execute_commits__custom_message(self):
        self.tool.options['pattern'] = '\d+'
        self.tool.options['message'] = 'You are bad.'
        self.tool.execute_commits(self.fixture_data)
        eq_(1, len(self.problems), 'Commits that do not match cause errors')
        msg = ('You are bad.\nThe pattern \d+ was not found in:\n'
               '* 6dcb09b5b57875f334f61aebed695e2e4193db5e\n')
        expected = IssueComment(msg)
        eq_(expected, self.problems.all()[0])

    @responses.activate
    def test_valid_url(self):
        responses.add(responses.GET, 'https://example.com/bugs', status=200)
        self.tool.options['pattern'] = '(bugs)'
        self.tool.options['check_url'] = 'https://example.com/{0}'
        self.tool.execute_commits(self.fixture_data)
        eq_(1, len(responses.calls), 'Valid URL is only checked once')
        eq_(0, len(self.problems), 'Valid 200 response with simple format')

    @responses.activate
    def test_valid_url_from_dictionary(self):
        responses.add(responses.GET, 'https://example.com/all', status=200)
        self.tool.options['pattern'] = '(\w+) (?P<ticket>\w+)'
        self.tool.options['check_url'] = 'https://example.com/{ticket}'
        self.tool.execute_commits(self.fixture_data)
        print('Calls '+str(len(responses.calls)))
        eq_(1, len(responses.calls), 'Valid URL is only checked once')
        eq_(0, len(self.problems), 'Valid 200 response with dictionary format')

    @responses.activate
    def test_invalid_url(self):
        responses.add(responses.GET, 'https://example.com/all', status=404)
        self.tool.options['pattern'] = '(\w+) (?P<ticket>\w+)'
        self.tool.options['check_url'] = 'https://example.com/{ticket}'
        self.tool.execute_commits(self.fixture_data)
        eq_(1, len(responses.calls), 'URL is only checked once')
        eq_(1, len(self.problems), 'Commits that do not match cause errors')
        msg = ('The following commits had issues.\n' +
               'These commits did not return a 200 response:\n' +
               '* 6dcb09b5b57875f334f61aebed695e2e4193db5e' +
               ' requested https://example.com/all and got a 404 response\n')
        expected = IssueComment(msg)
        eq_(expected, self.problems.all()[0])

    @responses.activate
    def test_good_url(self):
        fixture = load_fixture('commits-2.json')
        self.fixture_data = create_commits(fixture)
        responses.add(responses.GET, 'https://example.com/all', status=200)
        self.tool.options['pattern'] = '(\w+) (?P<ticket>\w+)'
        self.tool.options['check_url'] = 'https://example.com/{ticket}'
        self.tool.execute_commits(self.fixture_data)
        eq_(1, len(responses.calls), 'Valid URL is only checked once')
