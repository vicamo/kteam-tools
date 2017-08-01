#!/usr/bin/env python3
import yaml
import argparse
import os

# the so-trello root dir needs to be on PYTHONPATH
from trellotool.trellotool import TrelloTool


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
    def __init__(self, config_file, cycle):
        """
        :param config_file: yaml config file name
        :param cycle: cycle tag (e.g. '2017.07.01-1')
        """

        self.cycle = cycle
        self.config_file = config_file
        self.config = {}
        self.config_load()

        self.tt = TrelloTool()
        self.tt.assert_authenticated()

    def config_load(self):
        with open(self.config_file, 'r') as cfd:
            self.config = yaml.safe_load(cfd)

    def create(self):
        """
        Create the board, the lists and the cards form the config file

        :return: None
        """
        # create the board with the lists on the organization
        board = SRUBoard(self.tt, self.config['board']['prefix_name'] + self.cycle)
        board.create(self.config['board']['trello_organization'])
        board.add_lists(self.config['board']['lists'], self.config['board']['default_list'])

        # add the cards to the board, under the default list
        for card in self.config['cards']:
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
                board.add_card(card_name, card_desc)

        print("Board '%s' created: %s" % (board.name, board.url))

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='cli tool to create trello cards for SRU cycles')
    parser.add_argument('cycle', metavar='CYCLE', help='cycle tag', action='store')
    parser.add_argument('--config', metavar='CONFIG', help='config yaml file', required=False, action='store',
                        default='%s/create-sru-cards.yaml' % os.path.dirname(__file__))

    args = parser.parse_args()
    SRUCardsCreator(args.config, args.cycle).create()
