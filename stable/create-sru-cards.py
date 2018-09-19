#!/usr/bin/env python3
import yaml
import argparse
import os
import re
from datetime   import datetime, timedelta

# the so-trello root dir needs to be on PYTHONPATH
from trellotool.trellotool              import TrelloTool
from ktl.kernel_series                  import KernelSeries
from ktl.utils                          import run_command

class TrelloError(Exception):
    pass


class SRUBoard:
    def __init__(self, tt, name):
        """
        :param tt: TrelloTool object
        :param name: name of the board
        """
        self.tt = tt
        self.name = name
        self.id = None
        self.url = None
        self.default_list_name = None
        self.default_list_id = None

    def create(self, org):
        """
        Create the Trello board

        :param org: Trello organization (team)
        :return None
        """
        params = {
            'name': self.name,
            'idOrganization': org,
            'prefs_permissionLevel': 'org',
            'defaultLists': 'false'
        }

        self.tt.trello.board_create(**params)
        self.lookup_board_id()

    def lookup_board_id(self):
        for board in self.tt.trello.member_boards('me'):
            if board['name'] == self.name:
                self.id = board['id']
                self.url = board['url']
                return
        raise TrelloError("Could not find id for board '%s'" % self.name)

    def add_lists(self, list_names, default_list):
        """
        Add the lists to the board and save the default list
        to be used to later add the cards to

        :param list_names: list with the list names
        :param default_list: default list to add the cards to
        :return: None
        """
        for list_name in list_names:
            params = {
                'name': list_name,
                'pos': 'bottom'
            }
            self.tt.trello.board_addlist(self.id, **params)

        self.default_list_name = default_list
        self.lookup_list_id(default_list)

    def lookup_list_id(self, list_name):
        for board_list in self.tt.trello.board_lists(self.id):
            if board_list['name'] == list_name:
                self.default_list_id = board_list['id']
                return
        raise TrelloError("Could not find id for list '%s'" % list_name)

    def add_card(self, name, desc=None):
        """
        Add the given card to the default list board

        :param name: card name
        :param desc: card description
        :return: None
        """
        params = {
            'name': name,
            'pos': 'bottom',
        }
        if desc:
            params['desc'] = desc

        self.tt.trello.list_addcard(self.default_list_id, **params)


class SRUCardsCreator:
    def __init__(self, args):
        """
        :param args: argparse args object
        """

        self.args = args
        self.cycle = args.cycle
        self.config_file = args.config
        self.config = {}
        self.config_load()

        self.tt = TrelloTool()
        self.tt.assert_authenticated()

    def config_load(self):
        with open(self.config_file, 'r') as cfd:
            self.config = yaml.safe_load(cfd)

    def get_supported_series_sources(self):
        series_sources = []
        kernel_series = KernelSeries()

        for master_series in sorted(kernel_series.series, key=KernelSeries.key_series_name, reverse=True):
            if master_series.supported:
                for series in sorted(kernel_series.series, key=KernelSeries.key_series_name, reverse=True):
                    for source in sorted(series.sources, key=lambda x: x.name):
                        if not source.supported:
                            continue
                        if source.copy_forward:
                            continue
                        derived_from = source.derived_from
                        if derived_from:
                            if derived_from.series != master_series:
                                continue
                        else:
                            if series != master_series:
                                continue
                        series_sources.append((series, source))
        return series_sources

    def create(self):
        """
        Create the board, the lists and the cards form the config file

        :return: None
        """
        # create the board with the lists on the organization
        if self.args.dry_run:
            print('Create board: %s' % (self.config['board']['prefix_name'] + self.cycle))
        else:
            board = SRUBoard(self.tt, self.config['board']['prefix_name'] + self.cycle)
            board.create(self.config['board']['trello_organization'])
            board.add_lists(self.config['board']['lists'], self.config['board']['default_list'])

        # Cache the tuples (series, source) of supported sources
        series_sources_list = self.get_supported_series_sources()

        # add the cards to the board, under the default list
        for card in self.config['cards']:
            if card['name'] == 'Turn the crank':
                if self.args.crank_turn:
                    for (series, source) in series_sources_list:
                        card_name = 'Crank %s/%s' % (series.codename, source.name)
                        card_desc = None
                        if series.esm:
                            card_desc = 'ESM mode: Note different git location and build PPA'
                        if source.name == 'linux-euclid':
                            card_desc = 'No rebase to be done. Only needed if there are high and critical CVEs to be fixed.'
                        if self.args.dry_run:
                            print('Adding card: %s' % (card_name))
                            if card_desc:
                                print('             %s' % (card_desc))
                        else:
                            board.add_card(card_name, card_desc)
                continue
            if card['name'] == 'Produce kernel snaps':
                for (series, source) in series_sources_list:
                    for snap in sorted(source.snaps, key=lambda x: x.name):
                        if not snap.repo:
                            continue
                        card_name = 'Produce %s/%s snap' % (series.codename, snap.name)
                        card_desc = 'Update version in %s and push' % (snap.repo)
                        if self.args.dry_run:
                            print('Adding card: %s' % (card_name))
                            print('             %s' % (card_desc))
                        else:
                            board.add_card(card_name, card_desc)
                continue
            if card['name'] == 'Release kernel snaps':
                for (series, source) in series_sources_list:
                    for snap in sorted(source.snaps, key=lambda x: x.name):
                        if not snap.repo:
                            continue

                        card_name = 'Release %s/%s to candidate channel' % (series.codename, snap.name)
                        card_desc = 'Once the snap-release-to-candidate task in the tracking bug becomes confirmed'
                        if self.args.dry_run:
                            print('Adding card: %s' % (card_name))
                            print('             %s' % (card_desc))
                        else:
                            board.add_card(card_name, card_desc)

                        if not snap.stable:
                            continue

                        card_name = 'Release %s/%s to stable channel' % (series.codename, snap.name)
                        card_desc = 'Once the snap-release-to-stable task in the tracking bug becomes confirmed'
                        if self.args.dry_run:
                            print('Adding card: %s' % (card_name))
                            print('             %s' % (card_desc))
                        else:
                            board.add_card(card_name, card_desc)
                continue

            card_names = []
            if 'suffixes' in card:
                for suffix in card['suffixes']:
                    card_names.append("%s - %s" % (card['name'], suffix))
            else:
                card_names.append(card['name'])

            card_desc = None
            if 'description' in card:
                card_desc = card['description']

            for card_name in card_names:
                if self.args.dry_run:
                    print('Adding card: %s' % (card_name))
                    if card_desc:
                        print('             %s' % (card_desc))
                else:
                    board.add_card(card_name, card_desc)

        if not self.args.dry_run:
            print("Board '%s' created: %s" % (board.name, board.url))


def update_cycle_info(args):
    """
    Add a new entry on the sru-cycle info file for the given cycle.

    :param args: ArgumentParser Namespace object
    """
    file_name = args.cycle_info
    cycle = args.cycle
    # sanity check the cycle date (must be on the right format and be a monday)
    date_re = re.compile("^\d\d\d\d\.\d\d\.\d\d$")
    match = date_re.match(cycle)
    if match is not None:
        date = datetime.strptime(cycle, '%Y.%m.%d')
        if date.isoweekday() != 1:
            raise TrelloError('Date provided is not a Monday')

        release_date = date + timedelta(days=21)
        new_entry = "\'{0}\':\n    release-date: \'{1}\'".format(cycle,
                                                                 release_date.strftime('%Y-%m-%d'))

        with open(file_name, "r") as f:
            new_file = ""
            entry_added = False
            for line in f:
                if not entry_added and line[0] != "#":
                    # this should be the first non commented line of the file
                    new_file += "\n{0}\n".format(new_entry)
                    entry_added = True
                elif line.partition('\n')[0] == new_entry.partition('\n')[0]:
                    raise TrelloError('SRU cycle entry already present on the info file')
                new_file += line
        if not entry_added:
            raise('Could not find a place on the file for the new entry')

        print("Adding following entry to {0}".format(file_name))
        print("-----")
        print(new_entry)
        print("-----")
        if not args.dry_run:
            with open(file_name, "w") as f:
                f.write(new_file)

        # commit the file change
        commit_subject = "sru-cycle: Add {0} cycle info".format(cycle)
        if not args.dry_run:
            cmd = "git commit -sm '{0}' {1}".format(commit_subject, file_name)
            run_command(cmd)
        print("Added commit '{0}' to {1}".format(commit_subject, file_name))
    else:
        raise TrelloError('Wrong date format')


if __name__ == '__main__':
    retval = 0
    default_config = '%s/create-sru-cards.yaml' % os.path.dirname(__file__)
    default_cycle_info = '%s/../info/sru-cycle.yaml' % os.path.dirname(__file__)
    description = 'Create a Trello board with cards for SRU cycles'
    epilog = '''
The script reads the configuration from a yaml file, updates the sru-cycle info
yaml and creates a new Trello board and adds cards to it.

Examples:
    Run with the default options:
    $ create-sru-cards.py 2018.09.10

    Do not create anything, just print what would be done:
    $ create-sru-cards.py --dry-run 2018.09.10

    Create also the 'Turn the crank' cards:
    $ create-sru-cards.py --crank-turn 2018.09.10

    Do not add the new cycle entry to the cycle info file
    $ create-sru-cards.py --no-cycle-info 2018.09.10
'''.format(default_config)
    parser = argparse.ArgumentParser(description=description, epilog=epilog,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('cycle', metavar='CYCLE', help='cycle tag (expected format: YYYY.MM.DD)',
                        action='store')
    parser.add_argument('--config', metavar='CONFIG',
                        help='config yaml file (default: {0})'.format(default_config),
                        required=False, action='store', default=default_config)
    parser.add_argument('--cycle-info', metavar='CYCLE_INFO',
                        help='sru cycle info yaml file (default: {0})'.format(default_cycle_info),
                        required=False, action='store', default=default_cycle_info)
    parser.add_argument('--no-cycle-info', help='do not add an entry to the cycle info yaml file',
                        required=False, action='store_true', default=False)
    parser.add_argument('--crank-turn', help='create the \'Turn the crank\' cards (defaul: False)',
                        required=False, action='store_true', default=False)
    parser.add_argument('--dry-run', help='only print steps, no action done', required=False,
                        action='store_true', default=False)
    args = parser.parse_args()
    try:
        if not args.no_cycle_info:
            update_cycle_info(args)
        SRUCardsCreator(args).create()
    except TrelloError as e:
        retval = 1
        print('Error: {}'.format(e))

    exit(retval)
