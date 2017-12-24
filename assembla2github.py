""" utility for migrating github -> assembla """
import argparse
import dateutil.parser
import logging
import json
import string
import sys

# requires PyGithub library
import github

# map your assembla ticket statuses to Open or Closed here.
ASSEMBLA_TICKET_STATUS_TO_GITHUB_ISSUE_STATUS = {
    'New': 'open',
    'Accepted': 'open',
    'Test': 'open',
    'Invalid': 'closed',
    'Fixed': 'closed',
    'Demo': 'closed',
    'Review / Estimation': 'open',
}

# map your assembla user hashes to github logins here.
ASSEMBLA_USERID_TO_GITHUB_USERID = {
    'XXX': 'User1',
    'YYY': 'User2',
    'ZZZ': 'User3',
}

# the following field definitions should reconcile with the field schema in the json file
ASSEMBLA_MILESTONES_FIELDS = [
    'id',
    'due_date',
    'title',
    'user_id',
    'created_at',
    'created_by',
    'space_id',
    'description',
    'is_completed',
    'completed_date',
    'from_basecamp',
    'basecamp_milestone_id',
    'updated_at',
    'updated_by',
    'release_level',
    'release_notes',
    'planner_type',
    'start_date',
    'budget',
    'obstacles',
    'project_plan_type',
    'project_plan_url'
]

ASSEMBLA_TICKETS_FIELDS = [
    'id',
    'number',
    'reporter_id',
    'assigned_to_id',
    'space_id',
    'summary',
    'priority',
    'description',
    'created_on',
    'updated_at',
    'milestone_id',
    'component_id',
    'notification_list',
    'completed_date',
    'working_hours',
    'is_story',
    'importance',
    'story_importance',
    'permission_type',
    'ticket_status_id',
    'state',
    'estimate',
    'total_estimate',
    'total_invested_hours',
    'total_working_hours',
    'status_updated_at',
    'due_date',
    'milestone_updated_at',
]

ASSEMBLA_TICKET_STATUS_FIELDS = [
    'id',
    'space_tool_id',
    'name',
    'state',
    'list_order',
    'settings',
    'created_at',
    'updated_at'
]

ASSEMBLA_TICKET_COMMENT_FIELDS = [
    'id',
    'ticket_id',
    'user_id',
    'created_on',
    'updated_at',
    'comment',
    'ticket_changes',
    'rendered'
]

ASSEMBLA_MILESTONES = []
ASSEMBLA_TICKETS = []
ASSEMBLA_TICKET_STATUSES = []
ASSEMBLA_TICKET_COMMENTS = []
GITHUB_ISSUES = []
GITHUB_USERS = []
GITHUB_MILESTONES = []


def mapjsonlinetoassembblaobject(jsonstring, fieldlist, linenum, linetype):
    """
    converts json string -> dict
    :param jsonstring: string array "['a', 123, ...]"
    :param fieldlist: expected ordered list of fields expected in json array
    :param linenum: current line num
    :param linetype: for the error message report if needed. tells us the type of line we are trying to read
    :returns: a dict with the values from the jsonstring and the keys from the fieldlist
    """
    logging.debug('attempting to parse line #{0} as a {1}'.format(linenum, linetype))
    arr = json.loads(jsonstring)
    obj = {}
    if len(arr) != len(fieldlist):
        raise AssertionError('Assertion fail: {3} line [{0}] actual fields [{1}] != expected fields [{2}]'.format(linenum, len(arr), len(fieldlist), linetype))
    for i, field in enumerate(fieldlist):
        obj[field] = arr[i]
    return obj


def findgithubobjectbyassemblaid(assemblaid, githubobjectcollection):
    """
    :param assemblaid: the assembla id [#ID] assumed to be at the beginning of the title of the github object
    :param githubobjectcollection: the github objects to search
    :return: return the first match or None
    """
    return next(iter(filter(lambda x: x.title.startswith(assemblaid), githubobjectcollection)), None)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--verbose', '-v', required=False, default=False, help='verbose logging')
    parser.add_argument('--username', '-u', required=True, help='github username')
    parser.add_argument('--password', '-p', required=True, help='github password')
    parser.add_argument('--dumpfile', '-f', required=True, help='assembla dumpfile')
    parser.add_argument('--repository', '-r', required=True, help='github repository')
    runoptions = parser.parse_args()

    # log to stdout
    logging_level = logging.DEBUG if runoptions.verbose else logging.INFO
    root = logging.getLogger()
    root.setLevel(logging_level)
    channel = logging.StreamHandler(sys.stdout)
    channel.setLevel(logging_level)
    channel.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
    root.addHandler(channel)

    # read the file
    with open(runoptions.dumpfile, encoding='utf8') as filereader:
        # for each line determine the assembla object type, read all attributes to dict using the mappings
        # assign a key for each object which is used to link github <-> assembla objects to support updates
        for linenum, line in enumerate(filereader.readlines()):
            # remove all non printable characters from the line
            line = ''.join(x for x in line if x in string.printable)
            logging.debug('line #{0}: {1}'.format(linenum, line))
            if line.startswith('milestones, ['):
                currentline = line.replace('milestones, ', '').strip()
                milestone = mapjsonlinetoassembblaobject(currentline, ASSEMBLA_MILESTONES_FIELDS, linenum, 'milestones')
                milestone['githubtitle'] = '[#{0}] - {1}'.format(milestone['id'], milestone['title'])
                milestone['assemblakey'] = '[#{0}]'.format(milestone['id'])
                ASSEMBLA_MILESTONES.append(milestone)
            elif line.startswith('tickets, ['):
                currentline = line.replace('tickets, ', '').strip()
                ticket = mapjsonlinetoassembblaobject(currentline, ASSEMBLA_TICKETS_FIELDS, linenum, 'tickets')
                ticket['githubtitle'] = '[#{0}] - {1}'.format(ticket['number'], ticket['summary'])
                ticket['assemblakey'] = '[#{0}]'.format(ticket['number'])
                ASSEMBLA_TICKETS.append(ticket)
            elif line.startswith('ticket_statuses, ['):
                currentline = line.replace('ticket_statuses, ', '').strip()
                ticketstatus = mapjsonlinetoassembblaobject(currentline, ASSEMBLA_TICKET_STATUS_FIELDS, linenum, 'ticket statuses')
                ticketstatus['githubtitle'] = '[#{0}] - {1}'.format(ticketstatus['id'], ticketstatus['name'])
                ticketstatus['assemblakey'] = '[#{0}]'.format(ticketstatus['id'])
                ASSEMBLA_TICKET_STATUSES.append(ticketstatus)
            elif line.startswith('ticket_comments, ['):
                currentline = line.replace('ticket_comments, ', '').strip()
                ticketcomment = mapjsonlinetoassembblaobject(currentline, ASSEMBLA_TICKET_COMMENT_FIELDS, linenum, 'ticket comments')
                ticketcomment['assemblakey'] = '[#{0}]'.format(ticketcomment['id'])
                ticketcomment['createdate'] = dateutil.parser.parse(ticketcomment['created_on']).strftime('%Y-%m-%d %H:%M')
                ASSEMBLA_TICKET_COMMENTS.append(ticketcomment)

    # establish github connection
    ghub = github.Github(runoptions.username, runoptions.password)
    repo = ghub.get_repo(runoptions.repository)
    GITHUB_ISSUES = [x for x in repo.get_issues()]
    GITHUB_MILESTONES = [x for x in repo.get_milestones()]
    GITHUB_USERS = [x for x in repo.get_collaborators()]

    logging.info('Refreshing milestones->milestones...')
    for assemblamilestone in ASSEMBLA_MILESTONES:
        githubmilestone = findgithubobjectbyassemblaid(assemblamilestone['assemblakey'], GITHUB_MILESTONES)
        if not githubmilestone:
            logging.info('creating milestone: [{0}]'.format(assemblamilestone['githubtitle']))
            githubmilestone = repo.create_milestone(assemblamilestone['githubtitle'])
        else:
            logging.info('found existing milestone [{0}]'.format(assemblamilestone['githubtitle']))
        githubmilestone.edit(assemblamilestone['githubtitle'], description=assemblamilestone['description'])
    GITHUB_MILESTONES = repo.get_milestones()

    logging.info('Refreshing tickets->issues...')
    for assemblaticket in ASSEMBLA_TICKETS:
        assemblakey = assemblaticket['assemblakey']
        logging.info('Working on assembla ticket #{0}'.format(assemblakey))
        githubissue = findgithubobjectbyassemblaid(assemblakey, GITHUB_ISSUES)

        # create or find github issue using assembla key
        if not githubissue:
            logging.debug('Creating new issue: [{0}]'.format(assemblakey))
            githubissue = repo.create_issue(assemblaticket['githubtitle'], body=(assemblaticket['description'] or '(no description)'))
        else:
            logging.debug('Found existing issue: [{0}]'.format(assemblaticket['githubtitle']))

        logging.debug('Attempting to locate the milestone for assembla ticket #{0}'.format(assemblakey))
        assemblamilestone = next(iter(filter(lambda x: x['id'] == assemblaticket['milestone_id'], ASSEMBLA_MILESTONES)), None)

        # create or find github milestone using assembla key
        if assemblamilestone:
            logging.debug('Found assembla milestone for assembla ticket #{0}. Finding associated milestone.'.format(assemblakey))
            githubmilestone = findgithubobjectbyassemblaid(assemblamilestone['assemblakey'], GITHUB_MILESTONES) or github.GithubObject.NotSet

        logging.debug('Attempting to locate ticket status for assembla ticket #{0}'.format(assemblakey))
        assemblaticketstatus = next(iter(filter(lambda x: x['id'] == assemblaticket['ticket_status_id'], ASSEMBLA_TICKET_STATUSES)))
        githubissuestatus = ASSEMBLA_TICKET_STATUS_TO_GITHUB_ISSUE_STATUS.get(assemblaticketstatus['name'], 'open')

        logging.debug('Attempting to locate assigned user for assembla ticket #{0}'.format(assemblakey))
        githubuserid = ASSEMBLA_USERID_TO_GITHUB_USERID.get(assemblaticket['assigned_to_id'], None)
        githubuser = next(iter(filter(lambda x: x.login == githubuserid, GITHUB_USERS)), github.GithubObject.NotSet)

        logging.debug('Updating github issue for ticket #{0}'.format(assemblakey))
        assemblaticket['description'] = assemblaticket['description'] or '(no description)'
        githubissue.edit(assemblaticket['githubtitle'], body=assemblaticket['description'], milestone=githubmilestone, state=githubissuestatus, assignee=githubuser)

        # assembla ticket comments -> github issue comments
        logging.debug('Rebuilding issue comments for issue #{0}'.format(assemblaticket['assemblakey']))
        assemblaticketcomments = filter(lambda x: x['ticket_id'] == assemblaticket['id'], ASSEMBLA_TICKET_COMMENTS)

        # wipe out all the github issue comments and rebuild every time.
        # probably a better way but the github api has limited support for comment modification.
        for githubissuecomment in githubissue.get_comments():
            githubissuecomment.delete()
        for assemblaticketcomment in assemblaticketcomments:
            if assemblaticketcomment['comment']:
                githubissue.create_comment('({}) - {}'.format(assemblaticketcomment['createdate'], assemblaticketcomment['comment']))


if __name__ == "__main__":
    main()
