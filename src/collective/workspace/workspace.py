from BTrees.Length import Length
from BTrees.OOBTree import OOBTree
from .events import TeamMemberAddedEvent
from .membership import ITeamMembership
from .membership import TeamMembership
from zope.event import notify


class Workspace(object):
    """Provides access to team workspace functionality.

    This is registered as a behavior providing the IWorkspace interface.
    """

    def __init__(self, context):
        self.context = context

        # create a BTree to store team member data
        if not hasattr(self.context, '_team'):
            self.context._team = OOBTree()

        if not hasattr(self.context, '_counters'):
            self._recount()

    def _recount(self):
        counters = {}
        for name, func in self.counters:
            counters[name] = Length()
        for m in self.context._team.itervalues():
            for name, func in self.counters:
                if func(m):
                    counters[name].change(1)
        self.context._counters = counters

    @property
    def membership_schema(self):
        """Returns the schema to be used for editing team memberships.
        """
        return ITeamMembership

    membership_factory = TeamMembership

    # A list of groups to which team members can be assigned.
    # Maps group name -> roles
    available_groups = {
        u'Members': ('Contributor', 'Reader', 'TeamMember'),
        u'Admins': ('Contributor', 'Editor', 'Reviewer',
                    'Reader', 'TeamManager',),
    }

    counters = (
        ('members', lambda x: True),
    )

    @property
    def members(self):
        """Access the raw team member data."""
        return self.context._team

    def __getitem__(self, name):
        memberdata = self.context._team[name]
        return self.membership_factory(self, memberdata)

    def get(self, name, default=None):
        try:
            return self[name]
        except KeyError:
            return default

    def __iter__(self):
        for userid in self.context._team.iterkeys():
            yield self[userid]

    def add_to_team(self, **kw):
        """Makes sure a user is in this workspace's team.

        Pass user and any other attributes that should be set on the team member.
        """
        data = kw.copy()
        user = data['user']
        members = self.members
        if user not in self.members:
            if 'groups' not in data:
                data['groups'] = set()
            members[user] = data
            for name, func in self.counters:
                if func(data):
                    self.context._counters[name].change(1)
            membership = self.membership_factory(self, data)
            membership.handle_added()
            notify(TeamMemberAddedEvent(self.context, membership))
            self.context.reindexObject(idxs=['workspace_members'])
        else:
            membership = self.membership_factory(self, self.members[user])
            membership.update(data)
        return membership
