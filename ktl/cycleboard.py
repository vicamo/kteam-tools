import os
import yaml
from trellotool.trellotool              import TrelloTool

class CycleBoardError(Exception):
    pass

class CycleBoard:
    default_config = '%s/create-sru-cards.yaml' % os.path.dirname(__file__)

    def __init__(self):
        """
        :param tt: TrelloTool object
        :param name: name of the board
        """
        self.tt = TrelloTool()
        self.id = None
        self.url = None
        self.default_list_name = None
        self.default_list_id = None
        #self.load_config()

    def load_config(self):
        with open(self.default_config, 'r') as cfd2:
            self.config = yaml.safe_load(cfd2)

    def create(self, org, name):
        """
        Create the Trello board

        :param org: Trello organization (team)
        :return None
        """
        params = {
            'name': name,
            'idOrganization': org,
            'prefs_permissionLevel': 'org',
            'defaultLists': 'false'
        }

        self.tt.trello.board_create(**params)
        self.lookup_board_id(name)

    def lookup_board_id(self, name):
        for board in self.tt.trello.member_boards('me'):
            if board['name'] == name:
                self.id = board['id']
                self.url = board['url']
                self.name = board['name']
                return
        raise CycleBoardError("Could not find id for board '%s'" % name)

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
        raise CycleBoardError("Could not find id for list '%s'" % list_name)

    def set_default_list(self, list_name):
        for board_list in self.tt.trello.board_lists(self.id):
            if board_list['name'] == list_name:
                self.default_list_id = board_list['id']
                return
        raise CycleBoardError("Could not find id for list '%s'" % list_name)

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
